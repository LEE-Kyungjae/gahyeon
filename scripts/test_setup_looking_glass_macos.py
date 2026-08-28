#!/usr/bin/env python3

from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from setup_looking_glass_macos import (
    SetupError,
    find_bridge_app,
    find_installer,
    validate_go_display,
)


class LookingGlassMacosSetupTest(unittest.TestCase):
    def test_finds_versioned_bridge_application(self):
        with tempfile.TemporaryDirectory() as directory:
            app = Path(directory) / "Looking Glass Bridge 2.6.3.app"
            app.mkdir()
            self.assertEqual(app, find_bridge_app(Path(directory)))

    def test_chooses_newest_completed_official_installer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            older = root / "LookingGlassBridge-2.6.2.dmg"
            newer = root / "LookingGlassBridge-2.6.3.dmg"
            partial = root / "LookingGlassBridge-2.6.4.dmg.download"
            older.write_bytes(b"old")
            newer.write_bytes(b"new")
            partial.write_bytes(b"partial")
            older.touch()
            newer.touch()
            self.assertEqual(newer, find_installer(root))

    def test_requires_native_go_desktop_resolution(self):
        validate_go_display("Resolution: 1440 x 2560")
        with self.assertRaisesRegex(SetupError, "1440x2560"):
            validate_go_display("Resolution: 1920 x 1080")


if __name__ == "__main__":
    unittest.main()
