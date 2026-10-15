import datetime as dt
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "daemon"))
from nightbrightness import (
    normalize, fraction_for_schedule, fraction_from_kde, solar_minutes,
    BrightnessScheduler,
)


class DummyBus:
    def __init__(self):
        self.value = 5000
        self.maximum = 10000
        self.writes = []

    def raw_brightness(self, display):
        return self.value, self.maximum

    def set_brightness(self, display, raw):
        self.value = raw
        self.writes.append((display, raw))


class ScheduleTests(unittest.TestCase):
    def setUp(self):
        self.config = normalize({"enabled": True})

    def factor(self, hour, minute=0):
        return fraction_for_schedule(dt.datetime(2026, 10, 15, hour, minute), self.config)

    def test_day_and_night(self):
        self.assertEqual(self.factor(12), 0.0)
        self.assertEqual(self.factor(22), 1.0)
        self.assertEqual(self.factor(4), 1.0)

    def test_transitions(self):
        self.assertAlmostEqual(self.factor(8, 15), 0.5)
        self.assertAlmostEqual(self.factor(20, 15), 0.5)
        self.assertEqual(self.factor(8, 30), 0.0)

    def test_always_night(self):
        self.config["schedule_mode"] = "always"
        self.assertEqual(self.factor(12), 1.0)

    def test_follow_transition(self):
        self.assertAlmostEqual(fraction_from_kde(False, 1000, 1900, 30), 0.5)
        self.assertAlmostEqual(fraction_from_kde(True, 1000, 1900, 30), 0.5)
        self.assertEqual(fraction_from_kde(True, 0, 1900, 30), 0.0)

    def test_solar(self):
        result = solar_minutes(dt.date(2026, 6, 21), 0, 0)
        self.assertIsNotNone(result)
        sunrise, sunset = result
        offset = dt.datetime(2026, 6, 21, 12).astimezone().utcoffset()
        delta = offset.total_seconds() / 60 if offset else 0
        self.assertTrue(340 < sunrise - delta < 390)
        self.assertTrue(1060 < sunset - delta < 1110)

    def test_invalid_config(self):
        cfg = normalize({"day_brightness": 150, "night_brightness": -9,
                         "evening_time": "99:99", "display_id": "../../foo"})
        self.assertEqual(cfg["day_brightness"], 100)
        self.assertEqual(cfg["night_brightness"], 5)
        self.assertEqual(cfg["evening_time"], "20:00")
        self.assertEqual(cfg["display_id"], "display0")

    def test_disabled_does_not_write(self):
        bus = DummyBus()
        self.config["enabled"] = False
        self.assertEqual(BrightnessScheduler(bus).tick(self.config), "disabled")
        self.assertEqual(bus.writes, [])

    def test_write_and_manual_pause(self):
        bus = DummyBus()
        scheduler = BrightnessScheduler(bus)
        self.config["schedule_mode"] = "always"
        self.assertIn("set", scheduler.tick(self.config))
        self.assertEqual(bus.writes[-1], ("display0", 2500))
        bus.value = 6000
        self.assertEqual(scheduler.tick(self.config), "manual override")
        self.assertEqual(len(bus.writes), 1)


if __name__ == "__main__":
    unittest.main()
