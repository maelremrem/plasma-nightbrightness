# Plasma Night Brightness

**Experimental KDE Plasma 6 System Settings module for scheduling display brightness.**

Plasma Night Brightness changes your monitor's **hardware brightness** based on a day/night schedule through Plasma's own screen brightness D-Bus interface. It is independent of KDE's built-in **Night Light** (color temperature) feature.

> **Beta — 0.2.1:** Tested by an early user on Fedora 44 / KDE Plasma 6 with a Samsung monitor exposing `display0`. This is a **community project**, not an official KDE or Fedora package. Other displays, distributions and session setups may behave differently.

## Features

- Separate day and night brightness (5–100%)
- Fixed daily times, solar sunrise/sunset, or follow KDE Night Light
- Smooth transitions (0–120 minutes)
- Temporary pause after a manual adjustment
- Interactive OpenStreetMap coordinate picker
- Optional GeoClue2 location refresh every 1–24 hours
- Native System Settings page under **Display & Monitor**
- User-level systemd service; scheduling is **disabled by default**

## Requirements

- KDE Plasma 6 with a display supported by `org.kde.ScreenBrightness`
- Fedora 44 for the provided RPM build script (other distributions require their own packaging)
- Internet connection to fetch OpenStreetMap tiles for the map picker
- Optional GeoClue2 permission for automatic location

## Before installing: check monitor support

```bash
sudo dnf install qt6-qttools
qdbus-qt6 org.kde.ScreenBrightness /org/kde/ScreenBrightness org.kde.ScreenBrightness.DisplaysDBusNames
python3 tools/probe.py
python3 tools/probe.py --write-test
```

The write test briefly modifies the brightness then restores the previous value. A detected `display0` **alone** does not guarantee that writes will work.

## Build and install on Fedora 44

Clone this repository, then:

```bash
./build-rpm.sh --install-deps
sudo dnf install ./.rpmbuild/RPMS/x86_64/plasma-nightbrightness-0.2.1-1.fc44.x86_64.rpm
systemctl --user daemon-reload
systemctl --user enable --now nightbrightness.service
kcmshell6 kcm_nightbrightness
```

A precompiled RPM or COPR repository is **not available yet**. For now, compile locally with the supplied `.spec` file. The `-debuginfo` and `-debugsource` packages are optional.

Select your schedule and brightness, enable the module and click **Apply**. The user service does nothing to brightness until the `enabled` setting is turned on.

**If an earlier copy of the module's UI is shown** after upgrading, completely close System Settings and retry with:

```bash
QML_DISABLE_DISK_CACHE=1 kcmshell6 kcm_nightbrightness
```

## Diagnostics

```bash
python3 -m unittest discover -s tests -v
systemctl --user status nightbrightness.service
journalctl --user -u nightbrightness.service -n 60 --no-pager
/usr/libexec/nightbrightness-daemon --status
/usr/libexec/nightbrightness-daemon --once --dry-run
```

`--status` and `--once --dry-run` do not write brightness values.

## Uninstall

```bash
systemctl --user disable --now nightbrightness.service
sudo dnf remove plasma-nightbrightness
```

The user settings file in `~/.config/nightbrightness.json` is retained for potential reinstall. Removing the package does not reset the physical monitor's current brightness.

## Privacy

User settings and coordinates are stored locally at `~/.config/nightbrightness.json`. Automatic location requests go through the local system's GeoClue2 service only when the corresponding setting is enabled. The map uses an online OpenStreetMap tile provider; that provider can see normal network request metadata. No telemetry is built into the project.

## Known limitations

- Uses `display0` by default; there is no multi-monitor selector yet.
- Requires supported KDE D-Bus screen brightness methods.
- Direct brightness changes using monitor hardware buttons may not be detected as manual overrides.
- Polar day/night may have no valid sunrise/sunset event.
- Follow-KDE scheduling depends on KDE Night Light being enabled.
- QML and GeoClue2 behavior still needs wider testing and translations beyond the current mostly French UI.

## Project structure

- `src/` and `ui/`: C++ settings backend and QML user interface
- `daemon/`: Python scheduler
- `tools/`: hardware probe and optional GeoClue2 helper
- `systemd/`: per-user service
- `packaging/`: Fedora RPM specification
- `tests/`: Python unit tests

## Contributing

Bug reports, compatibility results, and pull requests are welcome. Include your Fedora/Plasma version, display model, and relevant logs (remove personal coordinates and usernames before posting).

Licensed under the [MIT License](LICENSE). Not affiliated with KDE or Fedora.
