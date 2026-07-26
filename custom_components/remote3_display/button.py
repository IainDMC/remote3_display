"""Maintenance buttons for Remote 3 Media Display."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN


BUTTONS = {
    "refresh_epg": ("Refresh EPG", "mdi:update"),
    "clear_artwork_cache": ("Clear artwork cache", "mdi:image-refresh"),
    "test_artwork": ("Test artwork selection", "mdi:image-search"),
    "reset_tivimate_data": ("Reset retained TiviMate data", "mdi:history"),
    "test_observer": ("Test TiviMate observer", "mdi:access-point-check"),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up maintenance buttons."""
    async_add_entities(
        [
            Remote3DisplayButton(hass, entry, key, name, icon)
            for key, (name, icon) in BUTTONS.items()
        ]
    )


class Remote3DisplayButton(ButtonEntity):
    """A maintenance action exposed as a Home Assistant button."""

    _attr_has_entity_name = False

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        action: str,
        name: str,
        icon: str,
    ) -> None:
        self.hass = hass
        self._entry = entry
        self._action = action
        self._attr_name = f"{entry.title} {name}"
        self._attr_icon = icon
        self._attr_unique_id = f"{entry.entry_id}_{action}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="IainDMC",
            model="Remote 3 Media Display",
            sw_version="2.2.0",
        )

    async def async_press(self) -> None:
        """Run the selected maintenance action."""
        entity = (
            self.hass.data.get(DOMAIN, {})
            .get("entries", {})
            .get(self._entry.entry_id, {})
            .get("media_player")
        )
        if entity is None:
            raise HomeAssistantError("Remote 3 media player is not ready")
        await entity.async_run_maintenance_action(self._action)
