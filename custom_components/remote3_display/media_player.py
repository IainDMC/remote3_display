"""Media player facade for Unfolded Circle Remote 3 display."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
import hashlib
from io import BytesIO
import json
import logging
import re
import secrets
import xml.etree.ElementTree as ET
from urllib.parse import urljoin

from aiohttp.web import Request, Response
import voluptuous as vol

from homeassistant.components import webhook
from homeassistant.components.http import KEY_HASS, HomeAssistantView
from homeassistant.components.media_player import (
    PLATFORM_SCHEMA,
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import CONF_NAME
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.storage import Store
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.util import dt as dt_util
from homeassistant.util import slugify

_LOGGER = logging.getLogger(__name__)

CONF_SOURCE_ENTITY = "source_entity"
CONF_APP_ENTITY = "app_entity"
CONF_APP_LOGOS = "app_logos"
CONF_APP_NAMES = "app_names"
CONF_FALLBACK_LOGO = "fallback_logo"
CONF_TMDB_TOKEN = "tmdb_token"
CONF_TMDB_ENABLED = "tmdb_enabled"
CONF_TMDB_LANGUAGE = "tmdb_language"
CONF_TIVIMATE_ENABLED = "tivimate_enabled"
CONF_TIVIMATE_APP_ID = "tivimate_app_id"
CONF_TIVIMATE_ADB_ENTITY = "tivimate_adb_entity"
CONF_TIVIMATE_CHANNEL_RESOURCE_ID = "tivimate_channel_resource_id"
CONF_TIVIMATE_PROGRAM_RESOURCE_ID = "tivimate_program_resource_id"
CONF_TIVIMATE_TIME_RESOURCE_ID = "tivimate_time_resource_id"
CONF_TIVIMATE_POLL_SECONDS = "tivimate_poll_seconds"
CONF_TIVIMATE_MODE = "tivimate_mode"
CONF_TIVIMATE_WEBHOOK_ID = "tivimate_webhook_id"
CONF_TIVIMATE_RETAIN_LAST = "tivimate_retain_last"
CONF_XTREAM_ENABLED = "xtream_enabled"
CONF_XTREAM_BASE_URL = "xtream_base_url"
CONF_XTREAM_USERNAME = "xtream_username"
CONF_XTREAM_PASSWORD = "xtream_password"
CONF_TIVIMATE_ARTWORK = "tivimate_artwork"
CONF_PLAYLIST_ENABLED = "playlist_enabled"
CONF_PLAYLIST_URL = "playlist_url"
CONF_PLAYLIST_URLS = "playlist_urls"
CONF_TIVIMATE_CHANNEL_ICON_SCALE = "tivimate_channel_icon_scale"

DOMAIN = "remote3_display"
DATA_ICON_ENTITIES = "icon_entities"
DATA_ICON_VIEW_REGISTERED = "icon_view_registered"

DEFAULT_NAME = "Remote 3 TV Room Display"
DEFAULT_FALLBACK_LOGO = "/local/icons/tv.png"
DEFAULT_TMDB_LANGUAGE = "en-US"
DEFAULT_TIVIMATE_APP_ID = "ar.tvplayer.tv"
DEFAULT_TIVIMATE_CHANNEL_RESOURCE_ID = "ar.tvplayer.tv:id/b7"
DEFAULT_TIVIMATE_PROGRAM_RESOURCE_ID = "ar.tvplayer.tv:id/152"
DEFAULT_TIVIMATE_TIME_RESOURCE_ID = "ar.tvplayer.tv:id/315"
DEFAULT_TIVIMATE_ARTWORK = "channel_icon"
DEFAULT_TIVIMATE_POLL_SECONDS = 3.0
DEFAULT_TIVIMATE_CHANNEL_ICON_SCALE = 100
REFRESH_SECONDS = 1
XTREAM_REFRESH = timedelta(hours=6)
XMLTV_HISTORY = timedelta(hours=6)
XMLTV_FUTURE = timedelta(hours=48)

ENTRY_DEFAULTS = {
    CONF_NAME: DEFAULT_NAME,
    CONF_APP_ENTITY: None,
    CONF_APP_LOGOS: {},
    CONF_APP_NAMES: {},
    CONF_FALLBACK_LOGO: DEFAULT_FALLBACK_LOGO,
    CONF_TMDB_ENABLED: False,
    CONF_TMDB_LANGUAGE: DEFAULT_TMDB_LANGUAGE,
    CONF_TIVIMATE_ENABLED: True,
    CONF_TIVIMATE_APP_ID: DEFAULT_TIVIMATE_APP_ID,
    CONF_TIVIMATE_CHANNEL_RESOURCE_ID: DEFAULT_TIVIMATE_CHANNEL_RESOURCE_ID,
    CONF_TIVIMATE_PROGRAM_RESOURCE_ID: DEFAULT_TIVIMATE_PROGRAM_RESOURCE_ID,
    CONF_TIVIMATE_TIME_RESOURCE_ID: DEFAULT_TIVIMATE_TIME_RESOURCE_ID,
    CONF_TIVIMATE_POLL_SECONDS: DEFAULT_TIVIMATE_POLL_SECONDS,
    CONF_TIVIMATE_MODE: "webhook",
    CONF_TIVIMATE_RETAIN_LAST: True,
    CONF_XTREAM_ENABLED: False,
    CONF_TIVIMATE_ARTWORK: DEFAULT_TIVIMATE_ARTWORK,
    CONF_PLAYLIST_ENABLED: True,
    CONF_PLAYLIST_URLS: [],
    CONF_TIVIMATE_CHANNEL_ICON_SCALE: 75,
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Required(CONF_SOURCE_ENTITY): cv.entity_id,
        vol.Optional(CONF_APP_ENTITY): cv.entity_id,
        vol.Optional(CONF_APP_LOGOS, default={}): {cv.string: cv.string},
        vol.Optional(CONF_APP_NAMES, default={}): {cv.string: cv.string},
        vol.Optional(CONF_FALLBACK_LOGO, default=DEFAULT_FALLBACK_LOGO): cv.string,
        vol.Optional(CONF_TMDB_TOKEN): cv.string,
        vol.Optional(CONF_TMDB_ENABLED, default=False): cv.boolean,
        vol.Optional(CONF_TMDB_LANGUAGE, default=DEFAULT_TMDB_LANGUAGE): cv.string,
        vol.Optional(CONF_TIVIMATE_ENABLED, default=False): cv.boolean,
        vol.Optional(CONF_TIVIMATE_APP_ID, default=DEFAULT_TIVIMATE_APP_ID): cv.string,
        vol.Optional(CONF_TIVIMATE_ADB_ENTITY): cv.entity_id,
        vol.Optional(
            CONF_TIVIMATE_CHANNEL_RESOURCE_ID,
            default=DEFAULT_TIVIMATE_CHANNEL_RESOURCE_ID,
        ): cv.string,
        vol.Optional(
            CONF_TIVIMATE_PROGRAM_RESOURCE_ID,
            default=DEFAULT_TIVIMATE_PROGRAM_RESOURCE_ID,
        ): cv.string,
        vol.Optional(
            CONF_TIVIMATE_TIME_RESOURCE_ID,
            default=DEFAULT_TIVIMATE_TIME_RESOURCE_ID,
        ): cv.string,
        vol.Optional(
            CONF_TIVIMATE_POLL_SECONDS, default=DEFAULT_TIVIMATE_POLL_SECONDS
        ): vol.All(vol.Coerce(float), vol.Range(min=1.0)),
        vol.Optional(CONF_TIVIMATE_MODE, default="adb"): vol.In(["adb", "webhook"]),
        vol.Optional(CONF_TIVIMATE_WEBHOOK_ID): cv.string,
        vol.Optional(CONF_TIVIMATE_RETAIN_LAST, default=True): cv.boolean,
        vol.Optional(CONF_XTREAM_ENABLED, default=False): cv.boolean,
        vol.Optional(CONF_XTREAM_BASE_URL): cv.url,
        vol.Optional(CONF_XTREAM_USERNAME): cv.string,
        vol.Optional(CONF_XTREAM_PASSWORD): cv.string,
        vol.Optional(
            CONF_TIVIMATE_ARTWORK, default=DEFAULT_TIVIMATE_ARTWORK
        ): vol.In(["channel_icon", "tmdb_poster"]),
        vol.Optional(CONF_PLAYLIST_ENABLED, default=False): cv.boolean,
        vol.Optional(CONF_PLAYLIST_URL): cv.url,
        vol.Optional(CONF_PLAYLIST_URLS, default=[]): vol.All(
            cv.ensure_list, [cv.url]
        ),
        vol.Optional(
            CONF_TIVIMATE_CHANNEL_ICON_SCALE,
            default=DEFAULT_TIVIMATE_CHANNEL_ICON_SCALE,
        ): vol.All(vol.Coerce(int), vol.Range(min=10, max=100)),
    }
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: dict,
    async_add_entities: AddEntitiesCallback,
    discovery_info: dict | None = None,
) -> None:
    """Import a legacy YAML platform into a UI config entry."""
    _LOGGER.info(
        "Importing YAML-configured Remote 3 display into the integration UI: %s",
        config[CONF_NAME],
    )
    await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_IMPORT},
        data=dict(config),
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a UI-configured media player."""
    config = {**ENTRY_DEFAULTS, **entry.data, **entry.options}
    for target, source in (
        (CONF_APP_NAMES, "app_names_json"),
        (CONF_APP_LOGOS, "app_logos_json"),
    ):
        if source in config and not config.get(target):
            try:
                parsed = json.loads(str(config[source] or "{}"))
                config[target] = parsed if isinstance(parsed, dict) else {}
            except (TypeError, ValueError):
                config[target] = {}
    entity = Remote3DisplayMediaPlayer(hass, config, entry.entry_id)
    domain_data = hass.data.setdefault(DOMAIN, {})
    domain_data.setdefault(DATA_ICON_ENTITIES, {})[entity.icon_entity_key] = entity
    domain_data.setdefault("entries", {}).setdefault(entry.entry_id, {})[
        "media_player"
    ] = entity
    if not domain_data.get(DATA_ICON_VIEW_REGISTERED):
        hass.http.register_view(Remote3DisplayChannelIconView())
        domain_data[DATA_ICON_VIEW_REGISTERED] = True
    async_add_entities([entity])


class Remote3DisplayChannelIconView(HomeAssistantView):
    """Serve a padded channel logo to clients holding its random image token."""

    url = "/api/remote3_display/channel-icon/{entity_key}"
    name = "api:remote3_display:channel_icon"
    # Remote 3 fetches entity artwork without a Home Assistant bearer token.
    # Access is instead limited by a high-entropy per-entity query token.
    requires_auth = False

    async def get(self, request: Request, entity_key: str) -> Response:
        entity = (
            request.app[KEY_HASS]
            .data.get(DOMAIN, {})
            .get(DATA_ICON_ENTITIES, {})
            .get(entity_key)
        )
        if entity is None:
            return Response(status=404, text="Unknown display entity")
        if not secrets.compare_digest(
            str(request.query.get("token") or ""), entity.icon_access_token
        ):
            return Response(status=403, text="Invalid image token")
        image = await entity.async_get_scaled_channel_icon()
        if image is None:
            return Response(status=404, text="Channel icon unavailable")
        body, content_type = image
        return Response(
            body=body,
            content_type=content_type,
            headers={"Cache-Control": "private, max-age=300"},
        )


class Remote3DisplayMediaPlayer(MediaPlayerEntity):
    """A read-only media player facade with app-logo artwork fallback."""

    _attr_has_entity_name = False
    _attr_device_class = MediaPlayerDeviceClass.TV
    _attr_supported_features = (
        MediaPlayerEntityFeature.PLAY
        | MediaPlayerEntityFeature.PAUSE
        | MediaPlayerEntityFeature.STOP
        | MediaPlayerEntityFeature.SEEK
        | MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.VOLUME_STEP
    )

    def __init__(
        self, hass: HomeAssistant, config: dict, entry_id: str | None = None
    ) -> None:
        """Initialize the facade."""
        self.hass = hass
        self._entry_id = entry_id
        self._attr_name = config[CONF_NAME]
        self._attr_unique_id = (
            f"{entry_id}_media_player" if entry_id is not None else None
        )
        self._source_entity = config[CONF_SOURCE_ENTITY]
        self._app_entity = config.get(CONF_APP_ENTITY)
        self._app_logos = config.get(CONF_APP_LOGOS, {})
        self._app_names = config.get(CONF_APP_NAMES, {})
        self._fallback_logo = config.get(CONF_FALLBACK_LOGO, DEFAULT_FALLBACK_LOGO)
        self._tmdb_token = config.get(CONF_TMDB_TOKEN)
        self._tmdb_enabled = config.get(CONF_TMDB_ENABLED, False)
        self._tmdb_language = config.get(CONF_TMDB_LANGUAGE, DEFAULT_TMDB_LANGUAGE)
        self._tmdb_for_tivimate = config.get("tmdb_for_tivimate", True)
        self._tmdb_for_other_apps = config.get("tmdb_for_other_apps", True)
        self._tmdb_minimum_match = int(config.get("tmdb_minimum_match", 60))
        self._tmdb_excluded_categories = {
            line.strip().casefold()
            for line in str(config.get("tmdb_excluded_categories_text", "")).splitlines()
            if line.strip()
        }
        self._tmdb_cache: dict[str, str | None] = {}
        self._tmdb_pending: set[str] = set()
        self._tivimate_enabled = config.get(CONF_TIVIMATE_ENABLED, True)
        self._tivimate_app_id = config.get(
            CONF_TIVIMATE_APP_ID, DEFAULT_TIVIMATE_APP_ID
        )
        self._tivimate_adb_entity = config.get(CONF_TIVIMATE_ADB_ENTITY)
        self._tivimate_channel_resource_id = config.get(
            CONF_TIVIMATE_CHANNEL_RESOURCE_ID, DEFAULT_TIVIMATE_CHANNEL_RESOURCE_ID
        )
        self._tivimate_program_resource_id = config.get(
            CONF_TIVIMATE_PROGRAM_RESOURCE_ID, DEFAULT_TIVIMATE_PROGRAM_RESOURCE_ID
        )
        self._tivimate_time_resource_id = config.get(
            CONF_TIVIMATE_TIME_RESOURCE_ID, DEFAULT_TIVIMATE_TIME_RESOURCE_ID
        )
        self._tivimate_poll_seconds = float(
            config.get(CONF_TIVIMATE_POLL_SECONDS, DEFAULT_TIVIMATE_POLL_SECONDS)
        )
        self._tivimate_mode = config.get(CONF_TIVIMATE_MODE, "webhook")
        self._tivimate_webhook_id = config.get(CONF_TIVIMATE_WEBHOOK_ID)
        self._tivimate_retain_last = config.get(CONF_TIVIMATE_RETAIN_LAST, True)
        self._inactive_behavior = config.get("inactive_behavior", "retain_mark")
        self._observer_stale_minutes = int(config.get("observer_stale_minutes", 15))
        self._xmltv_rollover_enabled = config.get("xmltv_rollover_enabled", True)
        self._rollover_grace_seconds = int(config.get("rollover_grace_seconds", 0))
        self._tivimate_channel = ""
        self._tivimate_program = ""
        self._tivimate_start: datetime | None = None
        self._tivimate_end: datetime | None = None
        self._tivimate_status = "waiting"
        self._tivimate_error = ""
        self._tivimate_category = ""
        self._xtream_enabled = config.get(CONF_XTREAM_ENABLED, False)
        self._xtream_base_url = config.get(CONF_XTREAM_BASE_URL)
        self._xtream_username = config.get(CONF_XTREAM_USERNAME)
        self._xtream_password = config.get(CONF_XTREAM_PASSWORD)
        self._tivimate_artwork = config.get(
            CONF_TIVIMATE_ARTWORK, DEFAULT_TIVIMATE_ARTWORK
        )
        self._tivimate_fallback_artwork = config.get(
            "tivimate_fallback_artwork", "tmdb_poster"
        )
        self._tivimate_channel_icon_scale = int(
            config.get(
                CONF_TIVIMATE_CHANNEL_ICON_SCALE,
                DEFAULT_TIVIMATE_CHANNEL_ICON_SCALE,
            )
        )
        self._icon_canvas_shape = config.get("icon_canvas_shape", "preserve")
        self._icon_background = config.get("icon_background", "transparent")
        self._show_progress = config.get("show_progress", True)
        self._show_channel_as_artist = config.get("show_channel_as_artist", True)
        self._show_program_as_title = config.get("show_program_as_title", True)
        self._show_next_program = config.get("show_next_program", True)
        self._icon_entity_key = slugify(self._attr_name)
        self._icon_access_token = secrets.token_urlsafe(24)
        self._scaled_icon_cache: dict[tuple, tuple[bytes, str]] = {}
        self._xtream_icons: dict[str, str] = {}
        self._xtream_pending = False
        self._xtream_last_attempt: datetime | None = None
        self._xtream_error = ""
        self._playlist_enabled = config.get(CONF_PLAYLIST_ENABLED, True)
        self._playlist_url = config.get(CONF_PLAYLIST_URL)
        self._playlist_urls = list(config.get(CONF_PLAYLIST_URLS, []))
        self._xmltv_schedule_enabled = config.get("xmltv_schedule_enabled", True)
        self._xmltv_refresh = timedelta(
            hours=float(config.get("xmltv_refresh_hours", 6))
        )
        self._xmltv_history = timedelta(
            hours=float(config.get("xmltv_history_hours", 6))
        )
        self._xmltv_future = timedelta(
            hours=float(config.get("xmltv_future_hours", 48))
        )
        self._epg_gap_behavior = config.get("epg_gap_behavior", "retain")
        self._prefer_later_playlist_source = config.get(
            "prefer_later_playlist_source", True
        )
        self._matching_mode = config.get("channel_matching_mode", "safe")
        self._channel_aliases = self._parse_aliases(
            config.get("channel_aliases_text", "")
        )
        self._remove_quality_suffixes = config.get(
            "remove_quality_suffixes", True
        )
        self._remove_small_characters = config.get(
            "remove_small_characters", True
        )
        self._custom_channel_suffixes = [
            line.strip()
            for line in str(
                config.get("custom_channel_suffixes_text", "")
            ).splitlines()
            if line.strip()
        ]
        self._channel_aliases = {
            self._normalize_channel(source): self._normalize_channel(target)
            for source, target in self._channel_aliases.items()
        }
        if self._playlist_url:
            self._playlist_urls.insert(0, self._playlist_url)
        self._playlist_urls = list(dict.fromkeys(self._playlist_urls))
        self._playlist_icons: dict[str, str] = {}
        self._xmltv_programs: dict[
            str, list[tuple[datetime, datetime, str, tuple[str, ...]]]
        ] = {}
        self._xmltv_program_count = 0
        self._tivimate_program_source = "observer"
        self._playlist_pending = False
        self._playlist_last_attempt: datetime | None = None
        self._playlist_error = ""
        self._tivimate_poll_pending = False
        self._tivimate_last_poll: datetime | None = None
        self._tivimate_last_received: datetime | None = None
        self._webhook_registered = False
        self._tivimate_store: Store = Store(
            hass, 1, f"remote3_display_{slugify(self._attr_name)}_tivimate"
        )
        self._unsub_state: CALLBACK_TYPE | None = None
        self._unsub_timer: CALLBACK_TYPE | None = None

    async def async_added_to_hass(self) -> None:
        """Register listeners."""
        await self._async_restore_tivimate()
        watched = [self._source_entity]
        if self._app_entity:
            watched.append(self._app_entity)
        self._unsub_state = async_track_state_change_event(
            self.hass, watched, self._handle_source_change
        )
        self._unsub_timer = async_track_time_interval(
            self.hass, self._handle_timer, timedelta(seconds=REFRESH_SECONDS)
        )
        if self._tivimate_enabled and self._tivimate_mode == "webhook":
            if not self._tivimate_webhook_id:
                self._tivimate_status = "missing tivimate_webhook_id"
            else:
                webhook.async_register(
                    self.hass,
                    "remote3_display",
                    f"{self.name} TiviMate Observer",
                    self._tivimate_webhook_id,
                    self._async_handle_tivimate_webhook,
                    local_only=True,
                )
                self._webhook_registered = True
                self._tivimate_status = (
                    "waiting for observer (last known restored)"
                    if self._tivimate_channel
                    else "waiting for observer"
                )
        self._schedule_xtream_refresh()
        self._schedule_playlist_refresh()

    async def async_will_remove_from_hass(self) -> None:
        """Remove listeners."""
        if self._unsub_state:
            self._unsub_state()
            self._unsub_state = None
        if self._unsub_timer:
            self._unsub_timer()
            self._unsub_timer = None
        if self._webhook_registered and self._tivimate_webhook_id:
            webhook.async_unregister(self.hass, self._tivimate_webhook_id)
            self._webhook_registered = False
        entities = self.hass.data.get(DOMAIN, {}).get(DATA_ICON_ENTITIES, {})
        entities.pop(self._icon_entity_key, None)
        if self._entry_id:
            entry_data = (
                self.hass.data.get(DOMAIN, {})
                .get("entries", {})
                .get(self._entry_id, {})
            )
            entry_data.pop("media_player", None)

    @property
    def icon_entity_key(self) -> str:
        return self._icon_entity_key

    @property
    def icon_access_token(self) -> str:
        return self._icon_access_token

    @callback
    def _handle_source_change(self, event) -> None:
        """Refresh when either source entity changes."""
        self._schedule_tivimate_poll()
        self._schedule_xtream_refresh()
        self._schedule_playlist_refresh()
        self._schedule_tmdb_lookup()
        self.async_write_ha_state()

    @callback
    def _handle_timer(self, now) -> None:
        """Refresh periodically so external clients resync."""
        self._schedule_tivimate_poll()
        self._schedule_xtream_refresh()
        self._schedule_playlist_refresh()
        if self._update_program_from_xmltv(now):
            self.hass.async_create_task(self._async_save_tivimate())
        self._schedule_tmdb_lookup()
        self.async_write_ha_state()

    @callback
    def _schedule_tivimate_poll(self) -> None:
        """Passively sample TiviMate's visible accessibility tree."""
        if not self._tivimate_enabled or self._tivimate_poll_pending:
            return
        if self.app_id != self._tivimate_app_id:
            should_clear = (
                self._inactive_behavior == "clear" or not self._tivimate_retain_last
            )
            if should_clear and (
                self._tivimate_channel or self._tivimate_program
            ):
                self._tivimate_channel = ""
                self._tivimate_program = ""
                self._tivimate_start = None
                self._tivimate_end = None
            self._tivimate_status = (
                "inactive (last known retained)"
                if self._inactive_behavior == "retain_mark"
                and self._tivimate_retain_last
                and self._tivimate_channel
                else "inactive"
            )
            self._tivimate_error = ""
            self._tivimate_last_poll = None
            return
        if self._tivimate_mode != "adb":
            return
        if not self._tivimate_adb_entity:
            self._tivimate_status = "missing tivimate_adb_entity"
            return
        now = dt_util.utcnow()
        if (
            self._tivimate_last_poll is not None
            and (now - self._tivimate_last_poll).total_seconds()
            < self._tivimate_poll_seconds
        ):
            return
        self._tivimate_last_poll = now
        self._tivimate_poll_pending = True
        self.hass.async_create_task(self._async_poll_tivimate())

    async def _async_handle_tivimate_webhook(
        self, hass: HomeAssistant, webhook_id: str, request: Request
    ) -> Response:
        """Receive event-driven TiviMate metadata from the Shield observer."""
        try:
            data = await request.json()
            channel = self._clean_channel_name(data.get("channel"))
            if not channel:
                return Response(status=400, text="Missing channel")
            program = self._clean_program_title(data.get("program"))
            time_range = str(data.get("time_range") or "").strip()
            changed = (
                channel != self._tivimate_channel
                or program != self._tivimate_program
            )
            self._tivimate_channel = channel
            self._tivimate_program = program
            self._tivimate_start, self._tivimate_end = self._parse_time_range(
                time_range
            )
            self._tivimate_program_source = "observer"
            self._tivimate_last_received = dt_util.utcnow()
            self._tivimate_status = "observer connected"
            self._tivimate_error = ""
            if changed:
                self._schedule_tmdb_lookup()
            await self._async_save_tivimate()
            self.async_write_ha_state()
            return Response(status=200, text="OK")
        except Exception as err:
            self._tivimate_status = "webhook error"
            self._tivimate_error = str(err)
            self.async_write_ha_state()
            return Response(status=400, text="Invalid payload")

    @callback
    def _schedule_xtream_refresh(self) -> None:
        """Refresh the Xtream channel-icon mapping at a conservative interval."""
        if (
            not self._xtream_enabled
            or self._xtream_pending
            or not self._xtream_base_url
            or not self._xtream_username
            or not self._xtream_password
        ):
            return
        now = dt_util.utcnow()
        if (
            self._xtream_last_attempt is not None
            and now - self._xtream_last_attempt < XTREAM_REFRESH
        ):
            return
        self._xtream_pending = True
        self._xtream_last_attempt = now
        self.hass.async_create_task(self._async_fetch_xtream_icons())

    async def _async_fetch_xtream_icons(self) -> None:
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(
                f"{self._xtream_base_url.rstrip('/')}/player_api.php",
                params={
                    "username": self._xtream_username,
                    "password": self._xtream_password,
                    "action": "get_live_streams",
                },
                timeout=30,
            ) as response:
                if response.status != 200:
                    raise ValueError(f"Xtream channel list returned HTTP {response.status}")
                data = await response.json(content_type=None)
            if not isinstance(data, list):
                raise ValueError("Xtream channel list was not a JSON array")
            icons = {}
            for stream in data:
                if not isinstance(stream, dict):
                    continue
                name = self._normalize_channel(stream.get("name"))
                icon = str(stream.get("stream_icon") or "").strip()
                if name and icon:
                    icons[name] = icon
            self._xtream_icons = icons
            self._xtream_error = ""
            self.async_write_ha_state()
        except Exception as err:
            self._xtream_error = str(err)
            _LOGGER.warning("Xtream channel-icon refresh failed: %s", err)
        finally:
            self._xtream_pending = False

    @callback
    def _schedule_playlist_refresh(self) -> None:
        """Refresh channel icons from an M3U playlist."""
        if (
            not self._playlist_enabled
            or not self._playlist_urls
            or self._playlist_pending
        ):
            return
        now = dt_util.utcnow()
        if (
            self._playlist_last_attempt is not None
            and now - self._playlist_last_attempt < self._xmltv_refresh
        ):
            return
        self._playlist_pending = True
        self._playlist_last_attempt = now
        self.hass.async_create_task(self._async_fetch_playlist_icons())

    async def _async_fetch_playlist_icons(self) -> None:
        session = async_get_clientsession(self.hass)
        try:
            icons: dict[str, str] = {}
            programs: dict[
                str, list[tuple[datetime, datetime, str, tuple[str, ...]]]
            ] = {}
            errors = []
            successful_sources = 0
            for index, source_url in enumerate(self._playlist_urls, start=1):
                try:
                    async with session.get(source_url, timeout=30) as response:
                        if response.status != 200:
                            raise ValueError(f"HTTP {response.status}")
                        playlist = await response.text(errors="replace")
                        final_url = str(response.url)
                    if "#EXTM3U" in playlist[:1000].upper():
                        source_icons = await self.hass.async_add_executor_job(
                            self._parse_m3u_icons, playlist, final_url
                        )
                        source_programs = {}
                    elif playlist.lstrip().startswith("<"):
                        now = dt_util.now()
                        source_icons, source_programs = (
                            await self.hass.async_add_executor_job(
                                self._parse_xmltv_data,
                                playlist,
                                final_url,
                                now - self._xmltv_history,
                                now + self._xmltv_future,
                            )
                        )
                        if not self._xmltv_schedule_enabled:
                            source_programs = {}
                    else:
                        raise ValueError("response was neither M3U nor XMLTV")
                    if self._prefer_later_playlist_source:
                        icons.update(source_icons)
                        programs.update(source_programs)
                    else:
                        for name, icon in source_icons.items():
                            icons.setdefault(name, icon)
                        for name, entries in source_programs.items():
                            programs.setdefault(name, entries)
                    successful_sources += 1
                except Exception as err:
                    # Never expose credential-bearing source URLs.
                    errors.append(f"source {index}: {err}")
            if successful_sources == 0:
                raise ValueError("; ".join(errors) or "No channel-data sources")
            self._playlist_icons = icons
            self._xmltv_programs = programs
            self._xmltv_program_count = sum(
                len(entries) for entries in programs.values()
            )
            self._playlist_error = "; ".join(errors)
            if self._update_program_from_xmltv(dt_util.now()):
                await self._async_save_tivimate()
                self._schedule_tmdb_lookup()
            self.async_write_ha_state()
        except Exception as err:
            self._playlist_error = str(err)
            _LOGGER.warning("M3U channel-icon refresh failed: %s", err)
        finally:
            self._playlist_pending = False

    def _parse_m3u_icons(self, playlist: str, final_url: str) -> dict[str, str]:
        """Return normalized channel-name to logo mappings from M3U."""
        icons: dict[str, str] = {}
        for line in playlist.splitlines():
            if not line.lstrip().upper().startswith("#EXTINF:"):
                continue
            logo_match = re.search(
                r"\btvg-logo\s*=\s*([\"'])(.*?)\1", line, re.IGNORECASE
            )
            if not logo_match or not logo_match.group(2).strip():
                continue
            logo = urljoin(final_url, logo_match.group(2).strip())
            names = []
            if "," in line:
                names.append(line.rsplit(",", 1)[1].strip())
            name_match = re.search(
                r"\btvg-name\s*=\s*([\"'])(.*?)\1", line, re.IGNORECASE
            )
            if name_match:
                names.append(name_match.group(2).strip())
            for name in names:
                normalized = self._normalize_channel(name)
                if normalized:
                    icons[normalized] = logo
        return icons

    def _parse_xmltv_data(
        self,
        guide: str,
        final_url: str,
        window_start: datetime,
        window_end: datetime,
    ) -> tuple[
        dict[str, str],
        dict[str, list[tuple[datetime, datetime, str, tuple[str, ...]]]],
    ]:
        """Return channel logos and programme schedules from XMLTV."""
        root = ET.fromstring(guide)
        icons: dict[str, str] = {}
        channel_names: dict[str, list[str]] = {}
        for channel in root.iter():
            if channel.tag.rsplit("}", 1)[-1] != "channel":
                continue
            names = []
            logo = ""
            for child in channel:
                tag = child.tag.rsplit("}", 1)[-1]
                if tag == "display-name" and child.text:
                    names.append(child.text.strip())
                elif tag == "icon" and child.attrib.get("src") and not logo:
                    logo = urljoin(final_url, child.attrib["src"].strip())
            if not logo:
                logo = ""
            normalized_names = []
            for name in names:
                normalized = self._normalize_channel(name)
                if normalized:
                    normalized_names.append(normalized)
                    if logo:
                        icons[normalized] = logo
            channel_id = str(channel.attrib.get("id") or "").strip()
            if channel_id and normalized_names:
                channel_names[channel_id] = normalized_names

        programs: dict[
            str, list[tuple[datetime, datetime, str, tuple[str, ...]]]
        ] = {}
        for programme in root.iter():
            if programme.tag.rsplit("}", 1)[-1] != "programme":
                continue
            names = channel_names.get(str(programme.attrib.get("channel") or ""))
            if not names:
                continue
            start = self._parse_xmltv_datetime(programme.attrib.get("start"))
            end = self._parse_xmltv_datetime(programme.attrib.get("stop"))
            if start is None or end is None or end <= start:
                continue
            # Keep entries that overlap the bounded schedule window. This also
            # retains a long programme that began before the history cutoff.
            if end <= window_start or start >= window_end:
                continue
            title = ""
            categories: list[str] = []
            for child in programme:
                child_tag = child.tag.rsplit("}", 1)[-1]
                if child_tag == "title" and child.text:
                    title = self._clean_program_title(child.text)
                elif child_tag == "category" and child.text:
                    categories.append(child.text.strip())
            if not title:
                continue
            entry = (start, end, title, tuple(categories))
            for name in names:
                programs.setdefault(name, []).append(entry)
        for entries in programs.values():
            entries.sort(key=lambda item: item[0])
        return icons, programs

    @staticmethod
    def _parse_xmltv_datetime(value) -> datetime | None:
        """Parse an XMLTV compact timestamp with an optional UTC offset."""
        text = str(value or "").strip()
        match = re.match(r"^(\d{14})(?:\s*([+-]\d{4}|Z))?", text)
        if not match:
            return None
        parsed = datetime.strptime(match.group(1), "%Y%m%d%H%M%S")
        offset = match.group(2)
        if offset == "Z":
            return parsed.replace(tzinfo=timezone.utc)
        if offset:
            return datetime.strptime(
                f"{match.group(1)} {offset}", "%Y%m%d%H%M%S %z"
            )
        return parsed.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)

    @staticmethod
    def _parse_aliases(value) -> dict[str, str]:
        """Parse one ``observed = guide`` channel alias per line."""
        aliases: dict[str, str] = {}
        for line in str(value or "").splitlines():
            separator = "->" if "->" in line else "=" if "=" in line else None
            if not separator:
                continue
            source, target = (part.strip() for part in line.split(separator, 1))
            if source and target:
                aliases[source.casefold()] = target.casefold()
        return aliases

    def _normalize_channel(self, value) -> str:
        """Normalize channel names for case/whitespace-insensitive matching."""
        return self._clean_channel_name(value).casefold()

    def _channel_match_tokens(self, value) -> tuple[str, ...]:
        """Return stable words used by the conservative logo fallback matcher."""
        normalized = self._normalize_channel(value)
        return tuple(re.findall(r"[a-z0-9]+", normalized, flags=re.IGNORECASE))

    def _clean_channel_name(self, value) -> str:
        """Remove small-form characters and display-quality suffixes."""
        original = " ".join(str(value or "").split())
        name = original
        if self._remove_small_characters:
            name = re.sub(
                "[\u00aa\u00b2\u00b3\u00b9\u00ba\u02b0-\u02ff"
                "\u1d00-\u1dbf\u2070-\u209f]",
                "",
                name,
            )
        suffixes = list(self._custom_channel_suffixes)
        if self._remove_quality_suffixes:
            suffixes = ["4K", "UHD", "FHD", *suffixes]
        if suffixes:
            suffix_pattern = "|".join(re.escape(item) for item in suffixes)
            suffix = re.compile(
                rf"(?:\s*[-–—|:]\s*)?(?:[\[(]\s*)?"
                rf"(?:{suffix_pattern})(?:\s*[\])])?\s*$",
                re.IGNORECASE,
            )
            while suffix.search(name):
                name = suffix.sub("", name).rstrip()
        return " ".join(name.split()).strip(" -–—|:") or original

        # Legacy cleanup retained below for reference and YAML compatibility.
        # Remove quality suffixes before small-form cleanup as some feeds use 4ᴷ.
        name = re.sub(
            r"(?:\s*[-–—|:]\s*)?(?:[\[(]\s*)?"
            r"(?:4[Kᴷᵏ]|UHD|FHD)(?:\s*[\])])?\s*$",
            "",
            original,
            flags=re.IGNORECASE,
        ).rstrip()
        name = re.sub(
            "[\u00aa\u00b2\u00b3\u00b9\u00ba\u02b0-\u02ff"
            "\u1d00-\u1dbf\u2070-\u209f]",
            "",
            name,
        )
        suffix = re.compile(
            r"(?:\s*[-–—|:]\s*)?(?:[\[(]\s*)?"
            r"(?:4K|UHD|FHD)(?:\s*[\])])?\s*$",
            re.IGNORECASE,
        )
        while suffix.search(name):
            name = suffix.sub("", name).rstrip()
        # Defensive token pass for unusual whitespace or punctuation forms.
        parts = name.split()
        while parts and parts[-1].strip("()[]{}-–—|:").upper() in {
            "4K",
            "UHD",
            "FHD",
        }:
            parts.pop()
        name = " ".join(parts)
        name = " ".join(name.split()).strip(" -–—|:")
        return name or original

    @staticmethod
    def _clean_program_title(value) -> str:
        """Remove display-incompatible trailing 'new' programme markers."""
        title = str(value or "").strip()
        return re.sub(
            r"\s+(?:ᴺᵉʷ|new|\(new\)|\[new\])\s*$",
            "",
            title,
            flags=re.IGNORECASE,
        ).rstrip()

    def _tivimate_channel_icon_match(self) -> tuple[str | None, str]:
        """Return the channel icon and the playlist key that supplied it.

        Exact normalized names remain authoritative.  The fallback only accepts
        a unique closest entry where one name's word set contains the other.
        This safely handles feed decorations such as ``US:`` or ``(WCBS)``
        without guessing between equally plausible stations.
        """
        channel = self._normalize_channel(self._tivimate_channel)
        if not channel:
            return None, ""
        if icon := self._playlist_icons.get(channel):
            return icon, channel
        if icon := self._xtream_icons.get(channel):
            return icon, channel

        matched = self._match_channel_key(channel, self._playlist_icons)
        if matched:
            return self._playlist_icons[matched], matched
        return None, ""

    def _tivimate_channel_icon(self) -> str | None:
        return self._tivimate_channel_icon_match()[0]

    def _scaled_channel_icon_url(self, icon_url: str) -> str:
        """Return a local endpoint whose query changes with the source logo."""
        digest = hashlib.sha256(icon_url.encode("utf-8")).hexdigest()[:12]
        return (
            f"/api/remote3_display/channel-icon/{self._icon_entity_key}"
            f"?token={self._icon_access_token}"
            f"&v={digest}-{self._tivimate_channel_icon_scale}"
            f"-{self._icon_canvas_shape}-{self._icon_background}"
        )

    async def async_get_scaled_channel_icon(self) -> tuple[bytes, str] | None:
        """Download, scale and cache the currently matched channel icon."""
        icon_url = self._tivimate_channel_icon()
        if not icon_url:
            return None
        cache_key = (
            icon_url,
            self._tivimate_channel_icon_scale,
            self._icon_canvas_shape,
            self._icon_background,
        )
        if cache_key in self._scaled_icon_cache:
            return self._scaled_icon_cache[cache_key]

        session = async_get_clientsession(self.hass)
        try:
            async with session.get(icon_url, timeout=15) as response:
                if response.status != 200:
                    raise ValueError(f"channel icon returned HTTP {response.status}")
                original = await response.read()
                original_type = response.headers.get("Content-Type", "image/png")
                original_type = original_type.split(";", 1)[0].strip()
            try:
                transformed = await self.hass.async_add_executor_job(
                    self._scale_icon_bytes,
                    original,
                    self._tivimate_channel_icon_scale,
                    self._icon_canvas_shape,
                    self._icon_background,
                )
                result = (transformed, "image/png")
            except Exception as err:
                # SVG and uncommon formats may not be supported by Pillow.
                _LOGGER.debug("Channel icon scaling fallback: %s", err)
                result = (original, original_type or "application/octet-stream")
            if len(self._scaled_icon_cache) >= 32:
                self._scaled_icon_cache.pop(next(iter(self._scaled_icon_cache)))
            self._scaled_icon_cache[cache_key] = result
            return result
        except Exception as err:
            _LOGGER.warning("Channel icon download failed: %s", err)
            return None

    @staticmethod
    def _scale_icon_bytes(
        original: bytes,
        scale_percent: int,
        canvas_shape: str,
        background: str,
    ) -> bytes:
        """Center a reduced raster logo on its original transparent canvas."""
        from PIL import Image

        with Image.open(BytesIO(original)) as source:
            image = source.convert("RGBA")
        width, height = image.size
        canvas_width, canvas_height = width, height
        if canvas_shape == "square":
            canvas_width = canvas_height = max(width, height)
        elif canvas_shape == "16:9":
            if width / height < 16 / 9:
                canvas_width = max(width, round(height * 16 / 9))
            else:
                canvas_height = max(height, round(width * 9 / 16))
        available_width = max(1, round(canvas_width * scale_percent / 100))
        available_height = max(1, round(canvas_height * scale_percent / 100))
        ratio = min(available_width / width, available_height / height)
        target = (
            max(1, round(width * ratio)),
            max(1, round(height * ratio)),
        )
        resized = image.resize(target, Image.Resampling.LANCZOS)
        colors = {
            "transparent": (0, 0, 0, 0),
            "black": (0, 0, 0, 255),
            "white": (255, 255, 255, 255),
            "automatic": (0, 0, 0, 0),
        }
        canvas = Image.new(
            "RGBA",
            (canvas_width, canvas_height),
            colors.get(background, colors["transparent"]),
        )
        canvas.alpha_composite(
            resized,
            ((canvas_width - target[0]) // 2, (canvas_height - target[1]) // 2),
        )
        output = BytesIO()
        canvas.save(output, format="PNG", optimize=True)
        return output.getvalue()

    def _match_channel_key(self, channel: str, choices) -> str:
        """Find one safe normalized channel-name match among choices."""
        normalized = self._normalize_channel(channel)
        normalized = self._channel_aliases.get(normalized, normalized)
        if normalized in choices:
            return normalized
        if self._matching_mode == "strict":
            return ""
        wanted = set(self._channel_match_tokens(normalized))
        if len(wanted) < 2:
            return ""
        matches: list[tuple[int, str]] = []
        for name in choices:
            candidate = set(self._channel_match_tokens(name))
            if len(candidate) < 2:
                continue
            if wanted <= candidate or candidate <= wanted:
                difference = len(wanted ^ candidate)
                if difference <= 2:
                    matches.append((difference, name))
        if not matches:
            return ""
        best_difference = min(item[0] for item in matches)
        best = [item for item in matches if item[0] == best_difference]
        return best[0][1] if len(best) == 1 else ""

    @callback
    def _update_program_from_xmltv(self, now: datetime) -> bool:
        """Advance a retained channel when its observer programme has ended."""
        if (
            not self._tivimate_enabled
            or not self._xmltv_schedule_enabled
            or not self._xmltv_rollover_enabled
            or self.app_id != self._tivimate_app_id
            or not self._tivimate_channel
            or not self._xmltv_programs
        ):
            return False
        # Do not replace fresh observer metadata before its advertised end.
        if self._tivimate_end is not None and now < (
            self._tivimate_end + timedelta(seconds=self._rollover_grace_seconds)
        ):
            return False
        channel_key = self._match_channel_key(
            self._tivimate_channel, self._xmltv_programs
        )
        if not channel_key:
            return False
        current = next(
            (
                entry
                for entry in self._xmltv_programs[channel_key]
                if entry[0] <= now < entry[1]
            ),
            None,
        )
        if current is None:
            if self._epg_gap_behavior == "clear" and self._tivimate_program:
                self._tivimate_program = ""
                self._tivimate_start = None
                self._tivimate_end = None
                self._tivimate_category = ""
                self._tivimate_program_source = "xmltv gap"
                return True
            if (
                self._epg_gap_behavior == "unavailable"
                and self._tivimate_program != "Programme unavailable"
            ):
                self._tivimate_program = "Programme unavailable"
                self._tivimate_start = None
                self._tivimate_end = None
                self._tivimate_category = ""
                self._tivimate_program_source = "xmltv gap"
                return True
            return False
        start, end, title, categories = current
        changed = (
            title != self._tivimate_program
            or start != self._tivimate_start
            or end != self._tivimate_end
        )
        if not changed:
            return False
        self._tivimate_program = title
        self._tivimate_start = start
        self._tivimate_end = end
        self._tivimate_category = ", ".join(categories)
        self._tivimate_program_source = "xmltv"
        self._schedule_tmdb_lookup()
        return True

    async def _async_poll_tivimate(self) -> None:
        try:
            await self._async_adb_shell(
                "uiautomator dump --compressed /sdcard/tivimate.xml"
            )
            xml_text = await self._async_adb_shell("cat /sdcard/tivimate.xml")
            start = xml_text.find("<?xml")
            end = xml_text.rfind("</hierarchy>")
            if start < 0 or end < 0:
                raise ValueError(
                    "Android Debug Bridge returned no UI XML "
                    f"(response length: {len(xml_text)})"
                )
            xml_text = xml_text[start : end + len("</hierarchy>")]
            root = ET.fromstring(xml_text)
            channel = ""
            program = ""
            time_range = ""
            for node in root.iter("node"):
                resource_id = node.attrib.get("resource-id")
                text = node.attrib.get("text", "").strip()
                if resource_id == self._tivimate_channel_resource_id and text:
                    channel = self._clean_channel_name(text)
                elif (
                    resource_id == self._tivimate_program_resource_id
                    and text
                    and not program
                ):
                    program = self._clean_program_title(text)
                elif resource_id == self._tivimate_time_resource_id and text:
                    time_range = text
            # The banner is transient. Keep the last successful values when hidden.
            if channel:
                changed = (
                    channel != self._tivimate_channel
                    or program != self._tivimate_program
                )
                self._tivimate_channel = channel
                self._tivimate_program = program
                self._tivimate_start, self._tivimate_end = self._parse_time_range(
                    time_range
                )
                self._tivimate_program_source = "observer"
                self._tivimate_last_received = dt_util.utcnow()
                if changed:
                    self._schedule_tmdb_lookup()
                    await self._async_save_tivimate()
                    self.async_write_ha_state()
                self._tivimate_status = "detected"
                self._tivimate_error = ""
            else:
                self._tivimate_status = "banner not visible"
                self._tivimate_error = ""
        except Exception as err:  # Home Assistant service errors vary by release.
            self._tivimate_status = "error"
            self._tivimate_error = str(err)
            _LOGGER.debug("Passive TiviMate read failed: %s", err)
        finally:
            self._tivimate_poll_pending = False

    async def _async_adb_shell(self, command: str) -> str:
        """Reuse the configured Android Debug Bridge integration connection."""
        registry_entry = er.async_get(self.hass).async_get(self._tivimate_adb_entity)
        if registry_entry is None or not registry_entry.config_entry_id:
            raise ValueError(
                f"{self._tivimate_adb_entity} is not a config-entry Android Debug Bridge entity"
            )
        config_entry = self.hass.config_entries.async_get_entry(
            registry_entry.config_entry_id
        )
        runtime_data = getattr(config_entry, "runtime_data", None)
        aftv = getattr(runtime_data, "aftv", None)
        if aftv is None or not hasattr(aftv, "adb_shell"):
            raise ValueError(
                f"{self._tivimate_adb_entity} does not belong to the Android Debug Bridge integration"
            )
        response = await aftv.adb_shell(command)
        if isinstance(response, bytes):
            return response.decode("utf-8", errors="replace")
        return response if isinstance(response, str) else ""

    @staticmethod
    def _parse_time_range(value: str) -> tuple[datetime | None, datetime | None]:
        """Convert an EPG clock range such as 16:00 - 16:30 to local datetimes."""
        times = re.findall(r"(?<!\d)([01]?\d|2[0-3]):([0-5]\d)(?!\d)", value)
        if len(times) < 2:
            return None, None

        now = dt_util.now()
        start = now.replace(
            hour=int(times[0][0]), minute=int(times[0][1]), second=0, microsecond=0
        )
        end = now.replace(
            hour=int(times[1][0]), minute=int(times[1][1]), second=0, microsecond=0
        )
        if end <= start:
            end += timedelta(days=1)
        # A programme spanning midnight may have started on the previous day.
        if start - now > timedelta(hours=12):
            start -= timedelta(days=1)
            end -= timedelta(days=1)
        return start, end

    async def _async_restore_tivimate(self) -> None:
        """Restore the durable last-known TiviMate metadata."""
        if not self._tivimate_retain_last:
            return
        data = await self._tivimate_store.async_load()
        if not isinstance(data, dict):
            return
        self._tivimate_channel = self._clean_channel_name(data.get("channel"))
        self._tivimate_program = self._clean_program_title(data.get("program"))
        self._tivimate_start = self._stored_datetime(data.get("start"))
        self._tivimate_end = self._stored_datetime(data.get("end"))
        self._tivimate_last_received = self._stored_datetime(
            data.get("last_received")
        )
        self._tivimate_category = str(data.get("category") or "")
        self._tivimate_program_source = str(data.get("program_source") or "restored")
        if self._tivimate_channel:
            self._tivimate_status = "restored last known"

    async def _async_save_tivimate(self) -> None:
        """Persist the last-known TiviMate metadata in Home Assistant storage."""
        if not self._tivimate_retain_last or not self._tivimate_channel:
            return
        await self._tivimate_store.async_save(
            {
                "channel": self._tivimate_channel,
                "program": self._tivimate_program,
                "start": self._tivimate_start.isoformat()
                if self._tivimate_start
                else None,
                "end": self._tivimate_end.isoformat()
                if self._tivimate_end
                else None,
                "last_received": self._tivimate_last_received.isoformat()
                if self._tivimate_last_received
                else None,
                "program_source": self._tivimate_program_source,
                "category": self._tivimate_category,
            }
        )

    @staticmethod
    def _stored_datetime(value) -> datetime | None:
        if not isinstance(value, str) or not value:
            return None
        return dt_util.parse_datetime(value)

    @callback
    def _schedule_tmdb_lookup(self) -> None:
        title = self.media_title
        is_tivimate = self.app_id == self._tivimate_app_id
        category = self._tivimate_category.casefold()
        if (
            not self._tmdb_enabled
            or not self._tmdb_token
            or not self._media_active()
            or not title
            or (is_tivimate and not self._tmdb_for_tivimate)
            or (not is_tivimate and not self._tmdb_for_other_apps)
            or (
                is_tivimate
                and any(item in category for item in self._tmdb_excluded_categories)
            )
            or title in self._tmdb_cache
            or title in self._tmdb_pending
        ):
            return

        self._tmdb_pending.add(title)
        self.hass.async_create_task(self._async_fetch_tmdb_poster(title))

    async def _async_fetch_tmdb_poster(self, title: str) -> None:
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(
                "https://api.themoviedb.org/3/search/multi",
                headers={
                    "Authorization": f"Bearer {self._tmdb_token}",
                    "Accept": "application/json",
                },
                params={
                    "query": title,
                    "language": self._tmdb_language,
                    "include_adult": "false",
                },
                timeout=10,
            ) as response:
                if response.status != 200:
                    _LOGGER.warning("TMDB lookup failed for %s: HTTP %s", title, response.status)
                    self._tmdb_cache[title] = None
                    return

                data = await response.json()
        except Exception as err:
            _LOGGER.warning("TMDB lookup failed for %s: %s", title, err)
            self._tmdb_cache[title] = None
            return
        finally:
            self._tmdb_pending.discard(title)

        poster_path = None
        for result in data.get("results", []):
            if result.get("media_type") not in ("movie", "tv"):
                continue
            result_title = str(result.get("title") or result.get("name") or "")
            score = SequenceMatcher(
                None, title.casefold(), result_title.casefold()
            ).ratio() * 100
            if score < self._tmdb_minimum_match:
                continue
            poster_path = result.get("poster_path")
            if poster_path:
                break

        self._tmdb_cache[title] = (
            f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None
        )
        self.async_write_ha_state()

    @property
    def _source_state(self):
        return self.hass.states.get(self._source_entity)

    @property
    def _app_state(self):
        if not self._app_entity:
            return None
        return self.hass.states.get(self._app_entity)

    def _source_attr(self, attr: str):
        state = self._source_state
        if state is None:
            return None
        return state.attributes.get(attr)

    def _app_attr(self, attr: str):
        state = self._app_state
        if state is None:
            return None
        return state.attributes.get(attr)

    def _mapped_name(self, value):
        if value is None:
            return None
        return self._app_names.get(value, value)

    def _media_active(self):
        if self.app_id == self._tivimate_app_id:
            return bool(self._tivimate_channel)
        if not self._source_attr("media_title"):
            return False

        source_app = self._mapped_name(
            self._source_attr("app_name") or self._source_attr("app_id")
        )
        current_app = self.app_name

        if source_app and current_app and source_app != current_app:
            return False

        return True

    @property
    def state(self):
        if self.app_id == self._tivimate_app_id and self._tivimate_channel:
            return "playing"
        if not self._media_active():
            return "idle"
        state = self._source_state
        return state.state if state is not None else None

    @property
    def app_id(self):
        return (
            self._app_attr("app_id")
            or self._app_attr("source")
            or self._source_attr("app_id")
        )

    @property
    def app_name(self):
        raw = (
            self._app_attr("app_name")
            or self._app_attr("source")
            or self._source_attr("app_name")
            or self.app_id
        )
        return self._mapped_name(raw)

    @property
    def media_title(self):
        if self.app_id == self._tivimate_app_id:
            return self._tivimate_program if self._show_program_as_title else ""
        if not self._media_active():
            return ""
        return self._source_attr("media_title")

    @property
    def media_artist(self):
        if self.app_id == self._tivimate_app_id:
            return self._tivimate_channel if self._show_channel_as_artist else ""
        if not self._media_active():
            return ""
        return self._source_attr("media_artist")

    @property
    def media_content_id(self):
        if self.app_id == self._tivimate_app_id:
            return self._tivimate_channel
        if not self._media_active():
            return ""
        return self._source_attr("media_content_id")

    @property
    def media_content_type(self):
        if not self._media_active():
            return "app"
        return self._source_attr("media_content_type") or "app"

    @property
    def media_duration(self):
        if not self._show_progress:
            return 0
        if (
            self.app_id == self._tivimate_app_id
            and self._tivimate_start
            and self._tivimate_end
        ):
            return max(0, (self._tivimate_end - self._tivimate_start).total_seconds())
        if not self._media_active():
            return 0
        return self._source_attr("media_duration")

    @property
    def media_position(self):
        if not self._show_progress:
            return 0
        if (
            self.app_id == self._tivimate_app_id
            and self._tivimate_start
            and self._tivimate_end
        ):
            duration = (self._tivimate_end - self._tivimate_start).total_seconds()
            elapsed = (dt_util.now() - self._tivimate_start).total_seconds()
            return min(max(0, elapsed), max(0, duration))
        if not self._media_active():
            return 0
        return self._source_attr("media_position")

    @property
    def media_position_updated_at(self):
        if not self._show_progress:
            return None
        if (
            self.app_id == self._tivimate_app_id
            and self._tivimate_start
            and self._tivimate_end
        ):
            return dt_util.utcnow()
        if not self._media_active():
            return dt_util.utcnow()
        updated = self._source_attr("media_position_updated_at")
        if updated is None:
            return None
        if isinstance(updated, str):
            return dt_util.parse_datetime(updated)
        return updated

    def _source_artwork(self):
        return (
            self._source_attr("entity_picture")
            or self._source_attr("entity_picture_local")
            or self._source_attr("media_image_url")
        )

    @property
    def media_image_url(self):
        """Return TMDB poster, real media artwork, or app logo."""
        if self._media_active():
            channel_icon = self._tivimate_channel_icon()
            tmdb_image = self._tmdb_cache.get(self.media_title)
            app_logo = (
                self._app_logos.get(self.app_name)
                or self._app_logos.get(self.app_id)
                or self._fallback_logo
            )
            if self.app_id == self._tivimate_app_id:
                choices = {
                    "channel_icon": (
                        self._scaled_channel_icon_url(channel_icon)
                        if channel_icon
                        and (
                            self._tivimate_channel_icon_scale < 100
                            or self._icon_canvas_shape != "preserve"
                            or self._icon_background != "transparent"
                        )
                        else channel_icon
                    ),
                    "tmdb_poster": tmdb_image,
                    "app_logo": app_logo,
                }
                for choice in (
                    self._tivimate_artwork,
                    self._tivimate_fallback_artwork,
                    "app_logo",
                ):
                    if choices.get(choice):
                        return choices[choice]
            if self.app_id != self._tivimate_app_id:
                if tmdb_image:
                    return tmdb_image
                image = self._source_artwork()
                if image:
                    return image

        return (
            self._app_logos.get(self.app_name)
            or self._app_logos.get(self.app_id)
            or self._fallback_logo
        )

    @property
    def media_image_remotely_accessible(self):
        image = self.media_image_url
        return bool(image and (image.startswith("http://") or image.startswith("https://")))

    @property
    def entity_picture(self):
        """Expose artwork in the plain entity_picture attribute as well."""
        return self.media_image_url

    @property
    def volume_level(self):
        return self._source_attr("volume_level")

    @property
    def is_volume_muted(self):
        return self._source_attr("is_volume_muted")

    def _next_xmltv_program(self):
        """Return the next scheduled programme for the current channel."""
        if not self._show_next_program or not self._tivimate_channel:
            return None
        channel_key = self._match_channel_key(
            self._tivimate_channel, self._xmltv_programs
        )
        if not channel_key:
            return None
        threshold = self._tivimate_end or dt_util.now()
        return next(
            (
                entry
                for entry in self._xmltv_programs[channel_key]
                if entry[0] >= threshold
            ),
            None,
        )

    def _artwork_source(self) -> str:
        image = self.media_image_url
        if not image:
            return "none"
        if "/api/remote3_display/channel-icon/" in image:
            return "scaled channel icon"
        if image == self._tivimate_channel_icon():
            return "channel icon"
        if image == self._tmdb_cache.get(self.media_title):
            return "TMDB poster"
        if image == self._source_artwork():
            return "source artwork"
        return "app logo"

    @property
    def extra_state_attributes(self):
        next_program = self._next_xmltv_program()
        observer_age = (
            max(
                0,
                (dt_util.utcnow() - self._tivimate_last_received).total_seconds(),
            )
            if self._tivimate_last_received
            else None
        )
        observer_health = (
            "never received"
            if observer_age is None
            else "stale"
            if observer_age > self._observer_stale_minutes * 60
            else "healthy"
        )
        return {
            "source_entity": self._source_entity,
            "app_entity": self._app_entity,
            "display_mode": "media" if self._media_active() else "app",
            "entity_picture": self.media_image_url,
            "tmdb_poster": self._tmdb_cache.get(self.media_title),
            "app_logo": (
                self._app_logos.get(self.app_name)
                or self._app_logos.get(self.app_id)
                or self._fallback_logo
            ),
            "tivimate_channel": self._tivimate_channel,
            "tivimate_program": self._tivimate_program,
            "tivimate_start": self._tivimate_start.isoformat()
            if self._tivimate_start
            else None,
            "tivimate_end": self._tivimate_end.isoformat()
            if self._tivimate_end
            else None,
            "tivimate_passive": self._tivimate_enabled,
            "tivimate_poll_seconds": self._tivimate_poll_seconds,
            "tivimate_mode": self._tivimate_mode,
            "tivimate_retain_last": self._tivimate_retain_last,
            "tivimate_adb_entity": self._tivimate_adb_entity,
            "tivimate_status": self._tivimate_status,
            "tivimate_error": self._tivimate_error,
            "tivimate_last_received": self._tivimate_last_received.isoformat()
            if self._tivimate_last_received
            else None,
            "tivimate_program_source": self._tivimate_program_source,
            "tivimate_category": self._tivimate_category,
            "tivimate_next_program": next_program[2] if next_program else None,
            "tivimate_next_start": next_program[0].isoformat()
            if next_program
            else None,
            "tivimate_next_end": next_program[1].isoformat()
            if next_program
            else None,
            "tivimate_next_category": ", ".join(next_program[3])
            if next_program
            else None,
            "tivimate_observer_health": observer_health,
            "tivimate_observer_age_seconds": round(observer_age, 1)
            if observer_age is not None
            else None,
            "tivimate_channel_icon": self._tivimate_channel_icon(),
            "tivimate_channel_icon_scale": self._tivimate_channel_icon_scale,
            "tivimate_icon_match": self._tivimate_channel_icon_match()[1],
            "artwork_source": self._artwork_source(),
            "xtream_icon_count": len(self._xtream_icons),
            "xtream_error": self._xtream_error,
            "playlist_icon_count": len(self._playlist_icons),
            "xmltv_channel_count": len(self._xmltv_programs),
            "xmltv_program_count": self._xmltv_program_count,
            "xmltv_history_hours": self._xmltv_history.total_seconds() / 3600,
            "xmltv_future_hours": self._xmltv_future.total_seconds() / 3600,
            "xmltv_refresh_hours": self._xmltv_refresh.total_seconds() / 3600,
            "xmltv_schedule_enabled": self._xmltv_schedule_enabled,
            "channel_matching_mode": self._matching_mode,
            "playlist_source_count": len(self._playlist_urls),
            "playlist_error": self._playlist_error,
        }

    async def async_media_play(self) -> None:
        await self.hass.services.async_call(
            "media_player",
            "media_play",
            {"entity_id": self._source_entity},
            blocking=False,
        )

    async def async_run_maintenance_action(self, action: str) -> None:
        """Run a user-requested maintenance action from a diagnostic button."""
        if action == "refresh_epg":
            if self._playlist_pending:
                return
            self._playlist_pending = True
            self._playlist_last_attempt = dt_util.utcnow()
            await self._async_fetch_playlist_icons()
        elif action == "clear_artwork_cache":
            self._tmdb_cache.clear()
            self._scaled_icon_cache.clear()
            self._schedule_tmdb_lookup()
        elif action == "reset_tivimate_data":
            self._tivimate_channel = ""
            self._tivimate_program = ""
            self._tivimate_start = None
            self._tivimate_end = None
            self._tivimate_last_received = None
            self._tivimate_category = ""
            self._tivimate_program_source = "observer"
            self._tivimate_status = "reset"
            self._tivimate_error = ""
            await self._tivimate_store.async_remove()
        elif action == "test_observer":
            if self._tivimate_last_received is None:
                self._tivimate_status = "observer test: no data received"
            else:
                age = (
                    dt_util.utcnow() - self._tivimate_last_received
                ).total_seconds()
                self._tivimate_status = (
                    "observer test: healthy"
                    if age <= self._observer_stale_minutes * 60
                    else "observer test: stale"
                )
        self.async_write_ha_state()

    async def async_media_pause(self) -> None:
        await self.hass.services.async_call(
            "media_player",
            "media_pause",
            {"entity_id": self._source_entity},
            blocking=False,
        )

    async def async_media_stop(self) -> None:
        await self.hass.services.async_call(
            "media_player",
            "media_stop",
            {"entity_id": self._source_entity},
            blocking=False,
        )

    async def async_media_seek(self, position: float) -> None:
        await self.hass.services.async_call(
            "media_player",
            "media_seek",
            {"entity_id": self._source_entity, "seek_position": position},
            blocking=False,
        )

    async def async_set_volume_level(self, volume: float) -> None:
        await self.hass.services.async_call(
            "media_player",
            "volume_set",
            {"entity_id": self._source_entity, "volume_level": volume},
            blocking=False,
        )

    async def async_mute_volume(self, mute: bool) -> None:
        await self.hass.services.async_call(
            "media_player",
            "volume_mute",
            {"entity_id": self._source_entity, "is_volume_muted": mute},
            blocking=False,
        )
