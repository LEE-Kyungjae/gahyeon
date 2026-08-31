#!/usr/bin/env python3

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class LookingGlassMacosRuntimeTest(unittest.TestCase):
    def test_launcher_enables_true_unreal_multiview_capture(self):
        launcher = (ROOT / "scripts/launch_looking_glass_macos_runtime.py").read_text()
        runtime = (ROOT / "unreal/GahyeonDesktopMetaHumanPOC/Source/"
                   "GahyeonDesktopMetaHumanPOC/Private/GahyeonDesktopMetaHumanPOC.cpp").read_text()
        encoder = (ROOT / "native/macos/GahyeonLookingGlassBridge/frame_encoder.mm").read_text()
        self.assertIn('runtime_environment["GAHYEON_LOOKING_GLASS_QUILT"] = "1"', launcher)
        self.assertIn("time.sleep(2.0)", launcher)
        self.assertIn("LookingGlassViewCount = 66", runtime)
        self.assertIn("PrepareLookingGlassView", runtime)
        self.assertIn("header->viewIndex", encoder)
        self.assertIn("quiltComplete", encoder)

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
