# Remote 3 Media Display

A Home Assistant custom media-player facade designed for Unfolded Circle Remote 3.

It combines media metadata from an existing Home Assistant player with Android TV
app detection and event-driven TiviMate metadata from the companion Shield observer.

## Features

- Standard media title, artist, duration, position, volume and artwork fields
- App-specific names and fallback logos
- Optional TMDB programme artwork
- Passive, event-driven TiviMate channel and programme detection
- Persistent last-known TiviMate metadata
- XMLTV channel-logo matching and automatic programme rollover
- Background XMLTV parsing with a bounded schedule window
- Optional channel-logo scaling for Remote 3
- Local light/dark Home Assistant brand artwork

## Installation with HACS

1. Open HACS in Home Assistant.
2. Open the three-dot menu and select **Custom repositories**.
3. Add `https://github.com/IainDMC/remote3_display`.
4. Select **Integration** as the category.
5. Install **Remote 3 Media Display**.
6. Restart Home Assistant.

HACS installs the component under:

```text
/config/custom_components/remote3_display/
```

New installations are configured from **Settings → Devices & services → Add
integration → Remote 3 Media Display**. Existing YAML installations remain
supported.

After setup, open the integration and select **Configure** to manage:

- artwork preference, fallback, icon size, canvas and background
- programme progress, title, channel and next-programme fields
- observer retention, stale threshold and inactive behaviour
- XMLTV rollover, refresh interval, bounded history/future windows and guide gaps
- strict/safe matching, channel aliases, suffix and superscript cleanup
- TMDB scope, language, confidence and excluded programme categories
- advanced ADB polling and TiviMate resource IDs

The integration also creates buttons to refresh the EPG, clear artwork caches,
reset retained TiviMate data, and test observer freshness.

## Updating

Install updates from HACS, then restart Home Assistant. GitHub releases are used as
the integration versions presented by HACS.

## Moving an existing YAML setup into the GUI

Version 2.0.1 automatically imports the existing
`media_player: - platform: remote3_display` YAML block:

1. Install the update and restart Home Assistant while the old YAML block is still
   present.
2. Open **Settings → Devices & services → Remote 3 Media Display**. The imported
   GUI entry uses the current YAML values, including values resolved through
   `!secret`.
3. Open **Configure** and confirm the settings.
4. Remove or comment out the old YAML block and restart again. The GUI entry then
   becomes the only source of configuration.

The import uses the existing values only when the GUI entry is first created.
Later GUI changes are not overwritten if the old YAML block is accidentally left
in place.

Private values entered in the integration UI are stored in Home Assistant's
config-entry storage. YAML users can continue using `!secret`.

## TiviMate Observer

For responsive detection without ADB polling, use `tivimate_mode: webhook` and the
companion TiviMate Observer accessibility service on the NVIDIA Shield. The webhook
is local-only and the observer listens only to TiviMate package `ar.tvplayer.tv`.

## Notes

- The integration domain remains `remote3_display`; the display name changed without
  breaking existing YAML.
- XMLTV sources refresh at startup and at most every six hours.
- Programme schedules retain entries overlapping the previous 6 hours and next 48
  hours.
- `tivimate_channel_icon_scale: 75` centers a 75% channel logo on a transparent
  canvas while leaving other artwork unchanged.

## Support

Report problems through [GitHub Issues](https://github.com/IainDMC/remote3_display/issues).

## License

MIT
