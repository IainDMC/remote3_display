"""Diagnostics for Remote 3 Media Display."""

from __future__ import annotations

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import DOMAIN

TO_REDACT = {
    "tmdb_token",
    "tivimate_webhook_id",
    "xtream_base_url",
    "xtream_username",
    "xtream_password",
    "playlist_url",
    "playlist_urls",
    "app_logos",
    "app_logos_json",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict:
    """Return a safe diagnostic snapshot."""
    entity = (
        hass.data.get(DOMAIN, {})
        .get("entries", {})
        .get(entry.entry_id, {})
        .get("media_player")
    )
    return {
        "entry": async_redact_data(
            {**entry.data, **entry.options}, TO_REDACT
        ),
        "runtime": entity.diagnostic_snapshot() if entity else {"ready": False},
    }
