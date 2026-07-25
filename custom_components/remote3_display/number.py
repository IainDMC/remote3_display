"""Device-page number controls for Remote 3 Media Display."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .config_entity import Remote3ConfigEntity


NUMBERS = {
    "tivimate_channel_icon_scale": (
        "Channel icon size",
        75,
        10,
        100,
        5,
        PERCENTAGE,
        "mdi:resize",
    ),
    "rollover_grace_seconds": (
        "Programme rollover grace",
        0,
        0,
        60,
        5,
        UnitOfTime.SECONDS,
        "mdi:timer-sand",
    ),
    "observer_stale_minutes": (
        "Observer stale timeout",
        15,
        1,
        120,
        1,
        UnitOfTime.MINUTES,
        "mdi:access-point-clock",
    ),
    "xmltv_refresh_hours": (
        "XMLTV refresh interval",
        6,
        1,
        24,
        1,
        UnitOfTime.HOURS,
        "mdi:update",
    ),
    "xmltv_history_hours": (
        "XMLTV history retained",
        6,
        0,
        24,
        1,
        UnitOfTime.HOURS,
        "mdi:history",
    ),
    "xmltv_future_hours": (
        "XMLTV future schedule",
        48,
        12,
        168,
        6,
        UnitOfTime.HOURS,
        "mdi:calendar-arrow-right",
    ),
    "tmdb_minimum_match": (
        "TMDB minimum title match",
        60,
        0,
        100,
        5,
        PERCENTAGE,
        "mdi:percent",
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up configuration number controls."""
    async_add_entities(
        [
            Remote3ConfigNumber(
                hass, entry, key, name, default, minimum, maximum, step, unit, icon
            )
            for key, (
                name,
                default,
                minimum,
                maximum,
                step,
                unit,
                icon,
            ) in NUMBERS.items()
        ]
    )


class Remote3ConfigNumber(Remote3ConfigEntity, NumberEntity):
    """A numeric integration option."""

    _attr_mode = NumberMode.SLIDER

    def __init__(
        self,
        hass,
        entry,
        key,
        name,
        default,
        minimum,
        maximum,
        step,
        unit,
        icon,
    ) -> None:
        super().__init__(hass, entry, key, name, default, icon)
        self._attr_native_min_value = minimum
        self._attr_native_max_value = maximum
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit

    @property
    def native_value(self) -> float:
        return float(self.config_value)

    async def async_set_native_value(self, value: float) -> None:
        await self.async_set_config_value(int(value))
