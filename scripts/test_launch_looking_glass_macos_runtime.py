#!/usr/bin/env python3

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class LookingGlassMacosRuntimeTest(unittest.TestCase):
    def test_one_stop_launcher_uses_canonical_unreal_and_native_bridge(self):
        source = (ROOT / "scripts/launch_looking_glass_macos_runtime.py").read_text()
        self.assertIn("launch_canonical_macos_runtime.py", source)
        self.assertIn("setup_looking_glass_macos.py", source)
        self.assertIn("GahyeonLookingGlassFrameEncoder", source)
        self.assertIn("stream_unreal_to_looking_glass.cjs", source)
        self.assertNotIn("desktop/package", source)
        self.assertNotIn("electron", source.lower())

    def test_stream_uses_dedicated_official_protocol_dependency(self):
        source = (ROOT / "scripts/stream_unreal_to_looking_glass.cjs").read_text()
        self.assertIn("native/macos/GahyeonLookingGlassBridge/node_modules/holoplay-core", source)
        self.assertNotIn("desktop/node_modules", source)


if __name__ == "__main__":
    unittest.main()
