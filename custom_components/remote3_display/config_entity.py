"""Shared helpers for device-page configuration entities."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity, EntityCategory

from . import DOMAIN


class Remote3ConfigEntity(Entity):
    """Base entity that stores a value in the config entry options."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_has_entity_name = True

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        key: str,
        name: str,
        default: Any,
        icon: str,
    ) -> None:
        self.hass = hass
        self._entry = entry
        self._key = key
        self._default = default
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{entry.entry_id}_config_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.options.get(
                "name", entry.data.get("name", entry.title)
            ),
            manufacturer="IainDMC",
            model="Remote 3 Media Display",
            sw_version="2.2.0",
        )

    @property
    def config_value(self) -> Any:
        """Return the effective option value."""
        return self._entry.options.get(
            self._key, self._entry.data.get(self._key, self._default)
        )

    async def async_set_config_value(self, value: Any) -> None:
        """Save an option and reload the integration."""
        options = {**self._entry.options, self._key: value}
        self.hass.config_entries.async_update_entry(
            self._entry, options=options
        )
        entity = (
            self.hass.data.get(DOMAIN, {})
            .get("entries", {})
            .get(self._entry.entry_id, {})
            .get("media_player")
        )
        if entity is not None and entity.apply_live_option(self._key, value):
            self.async_write_ha_state()
            return
        await self.hass.config_entries.async_reload(self._entry.entry_id)
