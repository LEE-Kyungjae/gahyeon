import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image

import build_predevice_quilt_v091 as quilt
import run_desktop_runtime_poc_v091 as runtime


class RuntimePocV091Tests(unittest.TestCase):
    def test_launch_is_game_mode_and_uses_configured_map(self):
        config = runtime.load_config(runtime.DEFAULT_CONFIG)
        engine = runtime.default_engine(config, "macos")
        command = runtime.build_command(runtime.ROOT, engine, config, Path("/tmp/test.log"), "macos")
        self.assertIn("-game", command)
        self.assertIn(config["map"], command)

    def test_windows_command_uses_win64_editor(self):
        config = runtime.load_config(runtime.DEFAULT_CONFIG)
        engine = runtime.default_engine(config, "windows")
        command = runtime.build_command(runtime.ROOT, engine, config, Path("C:/Temp/test.log"), "windows")
        self.assertTrue(command[0].replace("\\", "/").endswith("Engine/Binaries/Win64/UnrealEditor.exe"))
        self.assertIn("-game", command)

    def test_missing_prerequisites_are_reported_independently(self):
        present = Path(__file__)
        missing = Path(__file__).with_name("not-present.uproject")
        self.assertEqual([str(missing)], runtime.missing_prerequisites([str(present), str(missing)]))

    def test_quilt_is_explicitly_not_hardware_attestation(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.png"
            output = Path(folder) / "quilt.png"
            Image.new("RGB", (128, 72), "navy").save(source)
            report = quilt.build_quilt(source, output, quilt.DEFAULT_CONFIG)
            with Image.open(output) as image:
                self.assertEqual((4092, 4092), image.size)
            self.assertEqual("hardware-unverified", report["status"])
            self.assertFalse(report["physicalDeviceActive"])
            self.assertFalse(report["realParallaxCapture"])
            self.assertEqual(report, json.loads(output.with_suffix(".json").read_text()))


if __name__ == "__main__":
    unittest.main()
