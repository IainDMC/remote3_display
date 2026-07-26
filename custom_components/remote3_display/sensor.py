"""Diagnostic sensors for Remote 3 Media Display."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .config_entity import Remote3ConfigEntity


SENSORS = {
    "observer_health": ("Observer health", "never received", "mdi:access-point"),
    "observer_age": ("Observer age", None, "mdi:clock-outline"),
    "xmltv_last_refresh": ("XMLTV last refresh", None, "mdi:update"),
    "xmltv_program_count": ("XMLTV programme count", 0, "mdi:calendar-text"),
    "playlist_error": ("Playlist error", "", "mdi:alert-circle-outline"),
    "artwork_source": ("Artwork source", "none", "mdi:image-search"),
    "app_artwork_profile": ("Artwork profile", "default", "mdi:tune-variant"),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up diagnostic sensors."""
    async_add_entities(
        [
            Remote3DiagnosticSensor(hass, entry, key, name, default, icon)
            for key, (name, default, icon) in SENSORS.items()
        ],
        update_before_add=True,
    )


class Remote3DiagnosticSensor(Remote3ConfigEntity, SensorEntity):
    """A value sourced from the media facade diagnostic snapshot."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_should_poll = True

    def __init__(self, hass, entry, key, name, default, icon) -> None:
        super().__init__(hass, entry, f"diagnostic_{key}", name, default, icon)
        self._diagnostic_key = key
        self._value = default

    @property
    def native_value(self):
        return self._value

    async def async_update(self) -> None:
        entity = (
            self.hass.data.get("remote3_display", {})
            .get("entries", {})
            .get(self._entry.entry_id, {})
            .get("media_player")
        )
        if entity:
            self._value = entity.diagnostic_snapshot().get(
                self._diagnostic_key, self._default
            )
