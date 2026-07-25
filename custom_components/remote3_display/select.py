"""Device-page dropdown controls for Remote 3 Media Display."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .config_entity import Remote3ConfigEntity


SELECTS = {
    "tivimate_artwork": (
        "TiviMate artwork",
        "channel_icon",
        ["channel_icon", "tmdb_poster", "app_logo"],
        "mdi:image",
    ),
    "tivimate_fallback_artwork": (
        "TiviMate fallback artwork",
        "tmdb_poster",
        ["tmdb_poster", "channel_icon", "app_logo"],
        "mdi:image-off-outline",
    ),
    "icon_canvas_shape": (
        "Channel icon canvas",
        "preserve",
        ["preserve", "square", "16:9"],
        "mdi:aspect-ratio",
    ),
    "icon_background": (
        "Channel icon background",
        "transparent",
        ["transparent", "black", "white", "automatic"],
        "mdi:palette",
    ),
    "inactive_behavior": (
        "Inactive TiviMate behaviour",
        "retain_mark",
        ["retain_mark", "retain", "clear"],
        "mdi:television-off",
    ),
    "epg_gap_behavior": (
        "XMLTV guide gap behaviour",
        "retain",
        ["retain", "unavailable", "clear"],
        "mdi:calendar-alert",
    ),
    "channel_matching_mode": (
        "Channel matching mode",
        "safe",
        ["strict", "safe"],
        "mdi:link-variant",
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up configuration dropdowns."""
    async_add_entities(
        [
            Remote3ConfigSelect(hass, entry, key, name, default, options, icon)
            for key, (name, default, options, icon) in SELECTS.items()
        ]
    )


class Remote3ConfigSelect(Remote3ConfigEntity, SelectEntity):
    """A selectable integration option."""

    def __init__(
        self, hass, entry, key, name, default, options, icon
    ) -> None:
        super().__init__(hass, entry, key, name, default, icon)
        self._attr_options = options

    @property
    def current_option(self) -> str:
        return str(self.config_value)

    async def async_select_option(self, option: str) -> None:
        if option not in self._attr_options:
            raise ValueError(f"Unsupported option: {option}")
        await self.async_set_config_value(option)
