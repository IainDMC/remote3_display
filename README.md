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

This integration is configured with YAML. Copy `remote3_display.example.yaml` into
your Home Assistant package or merge its `media_player` entry into
`configuration.yaml`. Keep private tokens and playlist URLs in `secrets.yaml`.

## Updating

Install updates from HACS, then restart Home Assistant. GitHub releases are used as
the integration versions presented by HACS.

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
