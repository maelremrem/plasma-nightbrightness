#!/usr/bin/env python3
"""Plasma display brightness scheduler with local-time and KDE Night Light modes."""

import argparse
import datetime as dt
import json
import logging
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import tempfile

LOG = logging.getLogger("nightbrightness")
DEFAULTS = {
    "enabled": False,
    "day_brightness": 70,
    "night_brightness": 25,
    "schedule_mode": "fixed",
    "morning_time": "08:00",
    "evening_time": "20:00",
    "transition_minutes": 30,
    "manual_pause_minutes": 60,
    "latitude": 0.0,
    "longitude": 0.0,
    "sun_location_set": False,
    "location_auto": False,
    "location_refresh_hours": 6,
    "location_updated_at": 0,
    "display_id": "display0",
}
CONFIG = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "nightbrightness.json"
BRIGHTNESS_SERVICE = "org.kde.ScreenBrightness"
NIGHTLIGHT_SERVICE = "org.kde.KWin"
NIGHTLIGHT_PATH = "/org/kde/KWin/NightLight"
NIGHTLIGHT_IFACE = "org.kde.KWin.NightLight"


def clamp(value, lower, upper):
    return min(upper, max(lower, value))


def normalize(raw):
    data = DEFAULTS.copy()
    if not isinstance(raw, dict):
        return data
    for key in DEFAULTS:
        if key in raw:
            data[key] = raw[key]
    for key in ("day_brightness", "night_brightness"):
        try:
            data[key] = clamp(int(data[key]), 5, 100)
        except (TypeError, ValueError):
            data[key] = DEFAULTS[key]
    for key, upper in (("transition_minutes", 120), ("manual_pause_minutes", 240)):
        try:
            data[key] = clamp(int(data[key]), 0, upper)
        except (TypeError, ValueError):
            data[key] = DEFAULTS[key]
    for key, limits in (("latitude", (-90.0, 90.0)), ("longitude", (-180.0, 180.0))):
        try:
            coordinate = float(data[key])
            data[key] = clamp(coordinate, *limits) if math.isfinite(coordinate) else 0.0
        except (TypeError, ValueError):
            data[key] = 0.0
    for key in ("enabled", "sun_location_set", "location_auto"):
        data[key] = data[key] is True
    for key, low, high in (("location_refresh_hours", 1, 24), ("location_updated_at", 0, 2**53)):
        try:
            data[key] = clamp(int(data[key]), low, high)
        except (TypeError, ValueError, OverflowError):
            data[key] = DEFAULTS[key]
    if data["schedule_mode"] not in ("fixed", "sun", "follow", "always"):
        data["schedule_mode"] = "fixed"
    for key in ("morning_time", "evening_time"):
        if not isinstance(data[key], str) or re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", data[key]) is None:
            data[key] = DEFAULTS[key]
    if not isinstance(data["display_id"], str) or re.fullmatch(r"display\d+", data["display_id"]) is None:
        data["display_id"] = "display0"
    return data


def load_config():
    try:
        with CONFIG.open("r", encoding="utf-8") as file:
            return normalize(json.load(file))
    except FileNotFoundError:
        return DEFAULTS.copy()
    except (ValueError, OSError) as error:
        LOG.warning("Invalid configuration (%s); using safe defaults", error)
        return DEFAULTS.copy()


def parse_time(value):
    hours, minutes = map(int, value.split(":"))
    return hours * 60 + minutes


def solar_minutes(day, latitude, longitude):
    """Approximate local sunrise/sunset, with atmospheric refraction (-0.833°)."""
    n = day.timetuple().tm_yday
    year_length = 366 if (day.year % 4 == 0 and (day.year % 100 != 0 or day.year % 400 == 0)) else 365
    gamma = 2 * math.pi / year_length * (n - 1)
    eqtime = 229.18 * (
        0.000075 + 0.001868 * math.cos(gamma) - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma) - 0.040849 * math.sin(2 * gamma)
    )
    decl = (
        0.006918 - 0.399912 * math.cos(gamma) + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2 * gamma) + 0.000907 * math.sin(2 * gamma)
        - 0.002697 * math.cos(3 * gamma) + 0.00148 * math.sin(3 * gamma)
    )
    lat = math.radians(latitude)
    denominator = math.cos(lat) * math.cos(decl)
    if abs(denominator) < 1e-8:
        return None
    cosine_hour_angle = (math.cos(math.radians(90.833)) / denominator
                         - math.tan(lat) * math.tan(decl))
    if not -1 <= cosine_hour_angle <= 1:
        return None
    hour_angle = math.degrees(math.acos(cosine_hour_angle))
    noon_timestamp = time.mktime((day.year, day.month, day.day, 12, 0, 0, 0, 0, -1))
    offset = dt.datetime.fromtimestamp(noon_timestamp).astimezone().utcoffset()
    tz_minutes = offset.total_seconds() / 60 if offset else 0
    sunrise = 720 - 4 * (longitude + hour_angle) - eqtime + tz_minutes
    sunset = 720 - 4 * (longitude - hour_angle) - eqtime + tz_minutes
    return sunrise, sunset


def timed_events(day, config):
    mode = config["schedule_mode"]
    if mode == "fixed":
        morning = parse_time(config["morning_time"])
        evening = parse_time(config["evening_time"])
    elif mode == "sun":
        if not config["sun_location_set"]:
            return []
        solar = solar_minutes(day, config["latitude"], config["longitude"])
        if solar is None:
            return []
        morning, evening = solar
    else:
        return []
    origin = dt.datetime.combine(day, dt.time())
    return [(origin + dt.timedelta(minutes=morning), False),
            (origin + dt.timedelta(minutes=evening), True)]


def fraction_for_schedule(now, config):
    mode = config["schedule_mode"]
    if mode == "always":
        return 1.0
    if mode not in ("fixed", "sun"):
        return None
    events = []
    for days in (-3, -2, -1, 0, 1):
        events.extend(timed_events(now.date() + dt.timedelta(days=days), config))
    past = sorted((item for item in events if item[0] <= now), key=lambda item: item[0])
    if not past:
        return None
    event_time, to_night = past[-1]
    duration = config["transition_minutes"] * 60
    progress = clamp((now - event_time).total_seconds() / duration, 0, 1) if duration else 1
    return progress if to_night else 1 - progress


def fraction_from_kde(daylight, transition_start, now_timestamp, transition_minutes):
    duration = transition_minutes * 60
    if transition_start is None or transition_start <= 0 or duration == 0:
        return 0.0 if daylight else 1.0
    if transition_start > 10**12:
        transition_start /= 1000
    progress = clamp((now_timestamp - transition_start) / duration, 0, 1)
    return 1 - progress if daylight else progress


class PlasmaBus:
    def __init__(self):
        self.binary = shutil.which("qdbus-qt6") or shutil.which("qdbus6")
        if not self.binary:
            raise RuntimeError("qdbus-qt6 not found; install qt6-qttools")

    def call(self, service, path, method, *args):
        command = [self.binary, service, path, method] + [str(arg) for arg in args]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
        if completed.returncode:
            raise RuntimeError(completed.stderr.strip() or f"D-Bus call failed: {method}")
        return completed.stdout.strip()

    def raw_brightness(self, display):
        path = f"/org/kde/ScreenBrightness/{display}"
        interface = "org.kde.ScreenBrightness.Display"
        max_raw = int(self.call(BRIGHTNESS_SERVICE, path, interface + ".MaxBrightness"))
        raw = int(self.call(BRIGHTNESS_SERVICE, path, interface + ".Brightness"))
        if max_raw <= 0:
            raise RuntimeError("Invalid maximum brightness")
        return raw, max_raw

    def set_brightness(self, display, raw):
        path = f"/org/kde/ScreenBrightness/{display}"
        self.call(BRIGHTNESS_SERVICE, path, "org.kde.ScreenBrightness.Display.SetBrightness", raw, 1)

    def kde_night_fraction(self, config):
        enabled = self.call(NIGHTLIGHT_SERVICE, NIGHTLIGHT_PATH, NIGHTLIGHT_IFACE + ".enabled") == "true"
        if not enabled:
            return None
        daylight = self.call(NIGHTLIGHT_SERVICE, NIGHTLIGHT_PATH, NIGHTLIGHT_IFACE + ".daylight") == "true"
        previous = int(self.call(NIGHTLIGHT_SERVICE, NIGHTLIGHT_PATH,
                                 NIGHTLIGHT_IFACE + ".previousTransitionDateTime"))
        return fraction_from_kde(daylight, previous, time.time(), config["transition_minutes"])


def target_percentage(config, now, bus):
    if not config["enabled"]:
        return None
    if config["schedule_mode"] == "follow":
        fraction = bus.kde_night_fraction(config)
    else:
        fraction = fraction_for_schedule(now, config)
    if fraction is None:
        return None
    return (1 - fraction) * config["day_brightness"] + fraction * config["night_brightness"]


class LocationUpdater:
    """Opt-in refresh; location stays on device, no network API required."""
    def __init__(self):
        self.last_attempt = 0.0

    def tick(self, config):
        if not (config["enabled"] and config["schedule_mode"] == "sun"
                and config["location_auto"]):
            return
        now = time.time()
        period = config["location_refresh_hours"] * 3600
        if now - self.last_attempt < min(period, 900):
            return
        if now - config["location_updated_at"] < period:
            return
        self.last_attempt = now
        helper = "/usr/libexec/nightbrightness-geolocation"
        try:
            result = subprocess.run([helper], capture_output=True, text=True,
                                    timeout=25, check=True)
            latitude, longitude = map(float, result.stdout.strip().split())
            if not (math.isfinite(latitude) and math.isfinite(longitude)
                    and -90 <= latitude <= 90 and -180 <= longitude <= 180):
                raise ValueError("Invalid coordinates")
            # Re-read configuration to avoid overriding a user change during lookup.
            with CONFIG.open(encoding="utf-8") as file:
                raw = json.load(file)
            current = normalize(raw)
            if not (current["location_auto"] and current["schedule_mode"] == "sun"
                    and current["enabled"]):
                return
            raw.update(latitude=round(latitude, 6), longitude=round(longitude, 6),
                       sun_location_set=True, location_updated_at=int(time.time()))
            CONFIG.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="w", dir=CONFIG.parent,
                                             prefix=".nightbrightness-", delete=False) as tmp:
                temp_path = Path(tmp.name)
                os.chmod(temp_path, 0o600)
                json.dump(raw, tmp, indent=2)
                tmp.write("\n")
            os.replace(temp_path, CONFIG)
            LOG.info("Automatic location updated")
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
            LOG.warning("Location refresh failed; retaining last coordinates: %s", error)


class BrightnessScheduler:
    def __init__(self, bus):
        self.bus = bus
        self.last_applied = None
        self.last_display = None
        self.manual_until = 0.0
        self.previous_enabled = False
        self.last_error = None

    def tick(self, config, dry_run=False):
        if not config["enabled"]:
            self.last_applied = None
            self.previous_enabled = False
            return "disabled"
        if not self.previous_enabled:
            self.last_applied = None
            self.manual_until = 0
            self.previous_enabled = True
        target = target_percentage(config, dt.datetime.now(), self.bus)
        if target is None:
            self.last_applied = None
            return "waiting for schedule/location"
        display = config["display_id"]
        current, maximum = self.bus.raw_brightness(display)
        if self.last_display != display:
            self.last_applied = None
            self.last_display = display
        tolerance = max(1, round(maximum * 0.015))
        now_mono = time.monotonic()
        if self.last_applied is not None and abs(current - self.last_applied) > tolerance:
            self.manual_until = now_mono + config["manual_pause_minutes"] * 60
            self.last_applied = None
            LOG.info("Manual adjustment detected; pause for %d minutes", config["manual_pause_minutes"])
        if now_mono < self.manual_until:
            return "manual override"
        desired = round(maximum * target / 100)
        if abs(desired - current) <= max(1, round(maximum * 0.002)):
            self.last_applied = current
            return f"unchanged {target:.1f}%"
        if not dry_run:
            self.bus.set_brightness(display, desired)
            self.last_applied = desired
        return f"{'would set' if dry_run else 'set'} {target:.1f}% ({desired}/{maximum})"


def main():
    parser = argparse.ArgumentParser(description="KDE Plasma scheduled brightness service")
    parser.add_argument("--once", action="store_true", help="Apply the current target once")
    parser.add_argument("--dry-run", action="store_true", help="Never write brightness")
    parser.add_argument("--status", action="store_true", help="Print config and current target")
    args = parser.parse_args()
    logging.basicConfig(format="%(levelname)s %(message)s", level=logging.INFO)
    try:
        bus = PlasmaBus()
    except RuntimeError as error:
        parser.error(str(error))
    scheduler = BrightnessScheduler(bus)
    location_updater = LocationUpdater()
    if args.status:
        config = load_config()
        print("Display:", config["display_id"])
        print("Mode:", config["schedule_mode"])
        print("Enabled:", config["enabled"])
        print("Target:", target_percentage(config, dt.datetime.now(), bus))
        print("Current / Max:", bus.raw_brightness(config["display_id"]))
        return
    if args.once:
        print(scheduler.tick(load_config(), args.dry_run))
        return
    last_report = None
    while True:
        try:
            config = load_config()
            if not args.dry_run:
                location_updater.tick(config)
                config = load_config()
            message = scheduler.tick(config, args.dry_run)
            if message != last_report and not message.startswith("unchanged"):
                LOG.info("%s", message)
            last_report = message
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
            message = str(error)
            if message != last_report:
                LOG.warning("Waiting for KDE screen service: %s", error)
            last_report = message
            scheduler.last_applied = None
        time.sleep(15)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
