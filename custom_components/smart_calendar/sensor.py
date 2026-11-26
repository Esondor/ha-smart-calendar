"""Sensors: next chore, open today, waiting follow-ups."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    c = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    user = (c.data or {}).get("user", {}).get("name", "")
    async_add_entities([NextTask(c, entry, user), OpenToday(c, entry, user), Waiting(c, entry, user)])


class _Base(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, user, key, name, icon):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = f"{name} {user}".strip()
        self._attr_icon = icon


class NextTask(_Base):
    def __init__(self, c, e, u):
        super().__init__(c, e, u, "next", "Next task", "mdi:checkbox-marked-circle-outline")

    @property
    def native_value(self):
        t = (self.coordinator.data or {}).get("today") or []
        return t[0]["title"] if t else "None"

    @property
    def extra_state_attributes(self):
        t = (self.coordinator.data or {}).get("today") or []
        first = t[0] if t else {}
        ts = first.get("start")
        return {
            "start": dt_util.utc_from_timestamp(ts / 1000).isoformat() if ts else None,
            "location": first.get("location"), "task_id": first.get("taskId"),
            "today": [{"title": x["title"], "location": x.get("location"), "start": x.get("start"), "task_id": x.get("taskId")} for x in t],
        }


class OpenToday(_Base):
    _attr_native_unit_of_measurement = "tasks"

    def __init__(self, c, e, u):
        super().__init__(c, e, u, "open", "Open tasks", "mdi:format-list-checks")

    @property
    def native_value(self):
        return len((self.coordinator.data or {}).get("today") or [])


class Waiting(_Base):
    _attr_native_unit_of_measurement = "tasks"

    def __init__(self, c, e, u):
        super().__init__(c, e, u, "waiting", "Waiting", "mdi:timer-sand")

    @property
    def native_value(self):
        return len((self.coordinator.data or {}).get("waiting") or [])

    @property
    def extra_state_attributes(self):
        return {"tasks": [{"title": x["title"], "event": x.get("wait_event")} for x in (self.coordinator.data or {}).get("waiting") or []]}
