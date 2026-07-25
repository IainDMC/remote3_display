# TiviMate Observer for Android TV

TiviMate Observer is the companion Android accessibility service for Remote 3
Media Display. It watches only TiviMate (`ar.tvplayer.tv`) and sends the visible
channel, programme, and time range to a local Home Assistant webhook.

It is event-driven and does not use ADB polling, press remote-control buttons, or
make overlays appear.

## Install the APK on NVIDIA Shield

1. Download `TiviMateObserver-1.0.0.apk` from the matching GitHub release.
2. Sideload it onto the Shield using your preferred file manager or:

   ```text
   adb install -r TiviMateObserver-1.0.0.apk
   ```

3. Open **TiviMate Observer** on the Shield.
4. Enter the local Home Assistant base URL, such as
   `http://192.168.10.10:8123`.
5. Enter the same private webhook ID configured in Remote 3 Media Display.
6. Select **Save settings**.
7. Select **Open accessibility settings**, then enable **TiviMate Observer**.
8. Open TiviMate and change channel. Home Assistant should report
   `tivimate_status: observer connected`.

## Privacy and security

- The accessibility service is restricted to package `ar.tvplayer.tv`.
- It reads only the visible TiviMate channel banner fields needed by the
  integration.
- It sends data only to the Home Assistant URL and webhook ID entered on-device.
- It contains no embedded server address, credentials, Home Assistant token, or
  signing key.
- The webhook ID grants access to this local metadata endpoint and should be kept
  private.
- Plain HTTP is supported for trusted local networks. Use HTTPS when traffic
  crosses an untrusted network.

## Build from source

Requirements:

- JDK 17
- Android SDK 33
- Gradle 7.6.4

From this directory:

```text
gradle :app:assembleDebug
```

The APK is created at:

```text
app/build/outputs/apk/debug/app-debug.apk
```

GitHub Actions validates every observer change with a debug build. Repository
releases use the owner's private, stable signing key stored in GitHub Actions
secrets, so later APK versions can update the installed app without losing its
settings.
