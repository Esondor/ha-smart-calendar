"""Config flow: server address and personal access token; the tablet view link is created automatically."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_DISPLAY, CONF_TITLE, CONF_TOKEN, CONF_URL, DOMAIN


async def _check(hass, url: str, token: str) -> dict | None:
    try:
        async with async_get_clientsession(hass).get(url.rstrip("/") + "/api/ext/today", headers={"Authorization": f"Bearer {token}"}, timeout=15) as r:
            if r.status == 401:
                return {"base": "invalid_auth"}
            if r.status >= 400:
                return {"base": "cannot_connect"}
            return None
    except Exception:  # noqa: BLE001
        return {"base": "cannot_connect"}


class SmartCalendarFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            errors = await _check(self.hass, user_input[CONF_URL], user_input[CONF_TOKEN]) or {}
            if not errors:
                await self.async_set_unique_id(user_input[CONF_URL].rstrip("/") + "|" + user_input[CONF_TOKEN][-6:])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Smart Calendar", data=user_input)
        schema = vol.Schema({
            vol.Required(CONF_URL, default="https://"): str,
            vol.Required(CONF_TOKEN): str,
            vol.Optional(CONF_DISPLAY, default=""): str,
            vol.Optional(CONF_TITLE, default="Smart Calendar"): str,
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(entry):
        return OptionsFlow(entry)


class OptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry):
        self._entry = entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        conf = {**self._entry.data, **self._entry.options}
        return self.async_show_form(step_id="init", data_schema=vol.Schema({
            vol.Optional(CONF_DISPLAY, default=conf.get(CONF_DISPLAY, "")): str,
            vol.Optional(CONF_TITLE, default=conf.get(CONF_TITLE, "Smart Calendar")): str,
        }))
