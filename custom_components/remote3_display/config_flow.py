"""Config and options flows for Remote 3 Media Display."""

from __future__ import annotations

import json
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import OptionsFlow
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from . import DOMAIN


def _entity(domain: str) -> selector.EntitySelector:
    return selector.EntitySelector(
        selector.EntitySelectorConfig(domain=domain, multiple=False)
    )


def _select(options: list[str]) -> selector.SelectSelector:
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=options, mode=selector.SelectSelectorMode.DROPDOWN
        )
    )


def _number(minimum: float, maximum: float, step: float = 1) -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=minimum,
            max=maximum,
            step=step,
            mode=selector.NumberSelectorMode.SLIDER,
        )
    )


def _multiline() -> selector.TextSelector:
    return selector.TextSelector(
        selector.TextSelectorConfig(
            multiline=True, type=selector.TextSelectorType.TEXT
        )
    )


class Remote3DisplayConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Create a Remote 3 Media Display config entry."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> "Remote3DisplayOptionsFlow":
        return Remote3DisplayOptionsFlow()

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Collect the primary Home Assistant entities."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_tivimate()
        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default="Remote 3 TV Room Display"): str,
                vol.Required("source_entity"): _entity("media_player"),
                vol.Required("app_entity"): _entity("media_player"),
                vol.Optional("fallback_logo", default="/local/icons/tv.png"): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_import(self, import_data) -> FlowResult:
        """Convert a legacy media_player platform configuration."""
        data = dict(import_data or {})
        data.pop("platform", None)
        source_entity = str(data.get("source_entity") or "")
        app_entity = str(data.get("app_entity") or "")
        await self.async_set_unique_id(f"{source_entity}|{app_entity}")
        self._abort_if_unique_id_configured()
        title = str(data.get(CONF_NAME) or "Remote 3 Media Display")
        return self.async_create_entry(title=title, data=data)

    async def async_step_tivimate(self, user_input=None) -> FlowResult:
        """Collect observer and TiviMate settings."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_metadata()
        schema = vol.Schema(
            {
                vol.Required("tivimate_enabled", default=True): bool,
                vol.Required("tivimate_mode", default="webhook"): _select(
                    ["webhook", "adb"]
                ),
                vol.Optional("tivimate_webhook_id"): str,
                vol.Optional("tivimate_adb_entity"): _entity("media_player"),
                vol.Required(
                    "tivimate_app_id", default="ar.tvplayer.tv"
                ): str,
                vol.Required("tivimate_retain_last", default=True): bool,
            }
        )
        return self.async_show_form(step_id="tivimate", data_schema=schema)

    async def async_step_metadata(self, user_input=None) -> FlowResult:
        """Collect XMLTV and TMDB settings."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                for key in ("app_names_json", "app_logos_json"):
                    parsed = json.loads(str(user_input.get(key) or "{}"))
                    if not isinstance(parsed, dict):
                        raise ValueError(f"{key} must contain a JSON object")
                urls = [
                    line.strip()
                    for line in str(user_input.pop("playlist_urls_text", "")).splitlines()
                    if line.strip()
                ]
                user_input["playlist_urls"] = urls
                self._data.update(user_input)
                await self.async_set_unique_id(
                    f"{self._data['source_entity']}|{self._data['app_entity']}"
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=self._data[CONF_NAME], data=self._data
                )
            except ValueError:
                errors["base"] = "invalid_input"
        schema = vol.Schema(
            {
                vol.Required("playlist_enabled", default=True): bool,
                vol.Optional("playlist_urls_text"): _multiline(),
                vol.Required("tmdb_enabled", default=False): bool,
                vol.Optional("tmdb_token"): str,
                vol.Required("tmdb_language", default="en-US"): str,
                vol.Optional("app_names_json", default="{}"): _multiline(),
                vol.Optional("app_logos_json", default="{}"): _multiline(),
            }
        )
        return self.async_show_form(
            step_id="metadata", data_schema=schema, errors=errors
        )


class Remote3DisplayOptionsFlow(OptionsFlow):
    """Sectioned UI options."""

    async def async_step_init(self, user_input=None) -> FlowResult:
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "general",
                "display",
                "tivimate",
                "xmltv",
                "matching",
                "tmdb",
                "advanced",
            ],
        )

    def _values(self, schema: vol.Schema) -> vol.Schema:
        defaults = {**self.config_entry.data, **self.config_entry.options}
        return self.add_suggested_values_to_schema(schema, defaults)

    def _save(self, user_input: dict[str, Any]) -> FlowResult:
        return self.async_create_entry(
            data={**self.config_entry.options, **user_input}
        )

    async def async_step_general(self, user_input=None) -> FlowResult:
        """Edit entities, observer connection, sources and mapping data."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                for key in ("app_names_json", "app_logos_json"):
                    parsed = json.loads(str(user_input.get(key) or "{}"))
                    if not isinstance(parsed, dict):
                        raise ValueError(f"{key} must contain a JSON object")
                user_input["playlist_urls"] = [
                    line.strip()
                    for line in str(
                        user_input.pop("playlist_urls_text", "")
                    ).splitlines()
                    if line.strip()
                ]
                return self._save(user_input)
            except ValueError:
                errors["base"] = "invalid_input"
        values = {**self.config_entry.data, **self.config_entry.options}
        values["playlist_urls_text"] = "\n".join(values.get("playlist_urls", []))
        schema = vol.Schema(
            {
                vol.Required("source_entity"): _entity("media_player"),
                vol.Required("app_entity"): _entity("media_player"),
                vol.Required("fallback_logo", default="/local/icons/tv.png"): str,
                vol.Required("tivimate_enabled", default=True): bool,
                vol.Required("tivimate_mode", default="webhook"): _select(
                    ["webhook", "adb"]
                ),
                vol.Optional("tivimate_webhook_id"): str,
                vol.Optional("tivimate_adb_entity"): _entity("media_player"),
                vol.Required(
                    "tivimate_app_id", default="ar.tvplayer.tv"
                ): str,
                vol.Required("playlist_enabled", default=True): bool,
                vol.Optional("playlist_urls_text"): _multiline(),
                vol.Required("tmdb_enabled", default=False): bool,
                vol.Optional("tmdb_token"): str,
                vol.Optional("app_names_json", default="{}"): _multiline(),
                vol.Optional("app_logos_json", default="{}"): _multiline(),
            }
        )
        return self.async_show_form(
            step_id="general",
            data_schema=self.add_suggested_values_to_schema(schema, values),
            errors=errors,
        )

    async def async_step_display(self, user_input=None) -> FlowResult:
        if user_input is not None:
            return self._save(user_input)
        schema = vol.Schema(
            {
                vol.Required("tivimate_artwork", default="channel_icon"): _select(
                    ["channel_icon", "tmdb_poster", "app_logo"]
                ),
                vol.Required(
                    "tivimate_fallback_artwork", default="tmdb_poster"
                ): _select(["tmdb_poster", "channel_icon", "app_logo"]),
                vol.Required("tivimate_channel_icon_scale", default=75): _number(
                    10, 100, 5
                ),
                vol.Required("icon_canvas_shape", default="preserve"): _select(
                    ["preserve", "square", "16:9"]
                ),
                vol.Required("icon_background", default="transparent"): _select(
                    ["transparent", "black", "white", "automatic"]
                ),
                vol.Required("show_progress", default=True): bool,
                vol.Required("show_channel_as_artist", default=True): bool,
                vol.Required("show_program_as_title", default=True): bool,
                vol.Required("show_next_program", default=True): bool,
            }
        )
        return self.async_show_form(
            step_id="display", data_schema=self._values(schema)
        )

    async def async_step_tivimate(self, user_input=None) -> FlowResult:
        if user_input is not None:
            return self._save(user_input)
        schema = vol.Schema(
            {
                vol.Required("tivimate_retain_last", default=True): bool,
                vol.Required("xmltv_rollover_enabled", default=True): bool,
                vol.Required("rollover_grace_seconds", default=0): _number(
                    0, 60, 5
                ),
                vol.Required("observer_stale_minutes", default=15): _number(
                    1, 120, 1
                ),
                vol.Required("inactive_behavior", default="retain_mark"): _select(
                    ["retain_mark", "retain", "clear"]
                ),
            }
        )
        return self.async_show_form(
            step_id="tivimate", data_schema=self._values(schema)
        )

    async def async_step_xmltv(self, user_input=None) -> FlowResult:
        if user_input is not None:
            return self._save(user_input)
        schema = vol.Schema(
            {
                vol.Required("xmltv_schedule_enabled", default=True): bool,
                vol.Required("xmltv_refresh_hours", default=6): _number(1, 24, 1),
                vol.Required("xmltv_history_hours", default=6): _number(0, 24, 1),
                vol.Required("xmltv_future_hours", default=48): _number(
                    12, 168, 6
                ),
                vol.Required("epg_gap_behavior", default="retain"): _select(
                    ["retain", "unavailable", "clear"]
                ),
                vol.Required("prefer_later_playlist_source", default=True): bool,
            }
        )
        return self.async_show_form(
            step_id="xmltv", data_schema=self._values(schema)
        )

    async def async_step_matching(self, user_input=None) -> FlowResult:
        if user_input is not None:
            return self._save(user_input)
        schema = vol.Schema(
            {
                vol.Required("channel_matching_mode", default="safe"): _select(
                    ["strict", "safe"]
                ),
                vol.Optional("channel_aliases_text"): _multiline(),
                vol.Required("remove_quality_suffixes", default=True): bool,
                vol.Optional("custom_channel_suffixes_text"): _multiline(),
                vol.Required("remove_small_characters", default=True): bool,
            }
        )
        return self.async_show_form(
            step_id="matching", data_schema=self._values(schema)
        )

    async def async_step_tmdb(self, user_input=None) -> FlowResult:
        if user_input is not None:
            return self._save(user_input)
        schema = vol.Schema(
            {
                vol.Required("tmdb_enabled", default=False): bool,
                vol.Required("tmdb_language", default="en-US"): str,
                vol.Required("tmdb_for_tivimate", default=True): bool,
                vol.Required("tmdb_for_other_apps", default=True): bool,
                vol.Required("tmdb_minimum_match", default=60): _number(
                    0, 100, 5
                ),
                vol.Optional(
                    "tmdb_excluded_categories_text",
                    default="News\nSport\nWeather\nShopping",
                ): _multiline(),
            }
        )
        return self.async_show_form(
            step_id="tmdb", data_schema=self._values(schema)
        )

    async def async_step_advanced(self, user_input=None) -> FlowResult:
        if user_input is not None:
            return self._save(user_input)
        schema = vol.Schema(
            {
                vol.Required("tivimate_poll_seconds", default=3): _number(
                    1, 30, 1
                ),
                vol.Required(
                    "tivimate_channel_resource_id",
                    default="ar.tvplayer.tv:id/b7",
                ): str,
                vol.Required(
                    "tivimate_program_resource_id",
                    default="ar.tvplayer.tv:id/152",
                ): str,
                vol.Required(
                    "tivimate_time_resource_id",
                    default="ar.tvplayer.tv:id/315",
                ): str,
            }
        )
        return self.async_show_form(
            step_id="advanced", data_schema=self._values(schema)
        )
