import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "daemon"))
import nightbrightness as nb


class LocationTests(unittest.TestCase):
    def test_disabled_does_not_lookup(self):
        with patch.object(nb.subprocess, "run") as run:
            nb.LocationUpdater().tick(nb.normalize({"enabled": False, "schedule_mode": "sun",
                                                   "location_auto": True}))
            run.assert_not_called()

    def test_update_is_opt_in_and_persistent(self):
        with tempfile.TemporaryDirectory() as directory:
            conf = Path(directory) / "nightbrightness.json"
            conf.write_text(json.dumps({"enabled": True, "schedule_mode": "sun",
                                        "location_auto": True, "location_refresh_hours": 6}))
            with patch.object(nb, "CONFIG", conf), patch.object(nb.subprocess, "run") as run:
                run.return_value = Mock(stdout="44.84 -0.58\n")
                updater = nb.LocationUpdater()
                updater.tick(nb.load_config())
                data = json.loads(conf.read_text())
                self.assertAlmostEqual(data["latitude"], 44.84)
                self.assertTrue(data["sun_location_set"])
                self.assertGreater(data["location_updated_at"], 0)
                updater.tick(nb.load_config())
                self.assertEqual(run.call_count, 1)


if __name__ == "__main__":
    unittest.main()
