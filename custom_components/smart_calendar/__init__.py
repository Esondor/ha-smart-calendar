"""Smart Calendar: tablet view in the sidebar, sensors and an event service for automations."""
from __future__ import annotations

import logging
from datetime import timedelta

import voluptuous as vol

from homeassistant.components import frontend
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.network import NoURLAvailableError, get_url
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_DISPLAY, CONF_TITLE, CONF_TOKEN, CONF_URL, DOMAIN, PANEL_PATH

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor"]


class SmartCalendarApi:
    """Minimal client for the Smart Calendar token API."""

    def __init__(self, hass: HomeAssistant, url: str, token: str) -> None:
        self._session = async_get_clientsession(hass)
        self._url = url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {token}"}

    async def _req(self, method: str, path: str, json=None):
        async with self._session.request(method, self._url + path, headers=self._headers, json=json, timeout=20) as r:
            if r.status >= 400:
                raise UpdateFailed(f"{path}: HTTP {r.status}")
            return await r.json()

    async def today(self):
        return await self._req("GET", "/api/ext/today")

    async def event(self, name: str):
        return await self._req("POST", f"/api/ext/event/{name}", {})

    async def done(self, task_id: int):
        return await self._req("POST", f"/api/ext/tasks/{task_id}/done", {})

    async def display(self, origins: list[str]):
        return await self._req("POST", "/api/ext/display", {"origins": origins})


def _origins(hass: HomeAssistant) -> list[str]:
    """Addresses Home Assistant is opened with: the tablet view may be embedded there."""
    out = []
    for kw in ({"prefer_external": True}, {"prefer_external": False}, {"allow_internal": False}, {"allow_external": False}):
        try:
            u = get_url(hass, **kw)
        except NoURLAvailableError:
            continue
        if u not in out:
            out.append(u)
    return out


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    conf = {**entry.data, **{k: v for k, v in entry.options.items() if v}}
    api = SmartCalendarApi(hass, conf[CONF_URL], conf[CONF_TOKEN])
    coordinator = DataUpdateCoordinator(hass, _LOGGER, name=DOMAIN, update_method=api.today, update_interval=timedelta(minutes=1))
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"api": api, "coordinator": coordinator}

    # tablet view in the sidebar: without a link of its own, ask the server for one (once)
    if not conf.get(CONF_DISPLAY):
        try:
            res = await api.display(_origins(hass))
            hass.config_entries.async_update_entry(entry, data={**entry.data, CONF_DISPLAY: res["url"]})
            conf[CONF_DISPLAY] = res["url"]
            if not res.get("framed"):
                _LOGGER.warning("Smart Calendar: add your Home Assistant address under Administration → Displays → Home Assistant address so the tablet view can be shown")
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Smart Calendar: could not create the tablet view link: %s", err)
    if conf.get(CONF_DISPLAY):
        frontend.async_register_built_in_panel(
            hass, "iframe", sidebar_title=conf.get(CONF_TITLE) or "Smart Calendar", sidebar_icon="mdi:calendar-check",
            frontend_url_path=PANEL_PATH, config={"url": conf[CONF_DISPLAY]}, require_admin=False, update=True,
        )

    if not hass.services.has_service(DOMAIN, "event"):
        async def _event(call: ServiceCall) -> None:
            for data in hass.data.get(DOMAIN, {}).values():
                await data["api"].event(call.data["name"])
                await data["coordinator"].async_request_refresh()

        async def _done(call: ServiceCall) -> None:
            for data in hass.data.get(DOMAIN, {}).values():
                await data["api"].done(call.data["task_id"])
                await data["coordinator"].async_request_refresh()

        hass.services.async_register(DOMAIN, "event", _event, schema=vol.Schema({vol.Required("name"): cv.string}))
        hass.services.async_register(DOMAIN, "complete", _done, schema=vol.Schema({vol.Required("task_id"): cv.positive_int}))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_reload))
    return True


async def _reload(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if not hass.data.get(DOMAIN):
        frontend.async_remove_panel(hass, PANEL_PATH)
        hass.services.async_remove(DOMAIN, "event")
        hass.services.async_remove(DOMAIN, "complete")
    return ok
