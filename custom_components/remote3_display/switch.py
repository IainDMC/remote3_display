"""Device-page switches for Remote 3 Media Display."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .config_entity import Remote3ConfigEntity


SWITCHES = {
    "tivimate_enabled": ("TiviMate detection", True, "mdi:television-play"),
    "playlist_enabled": ("Playlist and XMLTV sources", True, "mdi:playlist-play"),
    "show_progress": ("Show programme progress", True, "mdi:progress-clock"),
    "show_channel_as_artist": ("Show channel name", True, "mdi:television-guide"),
    "show_program_as_title": ("Show programme title", True, "mdi:format-title"),
    "show_next_program": ("Show next programme", True, "mdi:skip-next"),
    "tivimate_retain_last": ("Retain last TiviMate data", True, "mdi:history"),
    "xmltv_rollover_enabled": (
        "Follow programme changes with XMLTV",
        True,
        "mdi:calendar-sync",
    ),
    "xmltv_schedule_enabled": ("Load XMLTV schedules", True, "mdi:calendar-clock"),
    "prefer_later_playlist_source": (
        "Prefer later playlist source",
        True,
        "mdi:playlist-check",
    ),
    "remove_quality_suffixes": (
        "Remove quality suffixes",
        True,
        "mdi:format-clear",
    ),
    "remove_small_characters": (
        "Remove superscript characters",
        True,
        "mdi:format-superscript",
    ),
    "tmdb_enabled": ("TMDB artwork", False, "mdi:movie-open-star"),
    "tmdb_for_tivimate": ("TMDB artwork for TiviMate", True, "mdi:television-classic"),
    "tmdb_for_other_apps": ("TMDB artwork for other apps", True, "mdi:apps"),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up configuration switches."""
    async_add_entities(
        [
            Remote3ConfigSwitch(hass, entry, key, name, default, icon)
            for key, (name, default, icon) in SWITCHES.items()
        ]
    )


class Remote3ConfigSwitch(Remote3ConfigEntity, SwitchEntity):
    """A boolean integration option."""

    @property
    def is_on(self) -> bool:
        return bool(self.config_value)

    async def async_turn_on(self, **kwargs) -> None:
        await self.async_set_config_value(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.async_set_config_value(False)
