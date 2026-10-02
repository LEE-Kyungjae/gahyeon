#!/usr/bin/env python3

import importlib.util
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("preflight_desktop_metahuman_poc.py")
SPEC = importlib.util.spec_from_file_location("desktop_metahuman_poc_preflight", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class DesktopMetaHumanPocPreflightTest(unittest.TestCase):
    def test_required_plugin_set_accepts_current_project(self):
        root = SCRIPT.parent.parent
        project_path = root / "unreal/GahyeonDesktopMetaHumanPOC/GahyeonDesktopMetaHumanPOC.uproject"
        import json
        project = json.loads(project_path.read_text(encoding="utf-8"))
        valid, missing = MODULE.validate_project_plugins(project)
        self.assertTrue(valid)
        self.assertEqual(missing, [])

    def test_missing_animation_data_fails_closed(self):
        valid, missing = MODULE.validate_project_plugins({"Plugins": []})
        self.assertFalse(valid)
        self.assertIn("AnimationData", missing)

    def test_available_memory_uses_pressure_percentage(self):
        outputs = {
            ("sysctl", "-n", "hw.memsize"): str(16 * 1024**3),
            ("memory_pressure", "-Q"): "System-wide memory free percentage: 40%",
        }
        with mock.patch.object(MODULE, "command_output", side_effect=lambda *args: outputs[args]):
            self.assertEqual(MODULE.available_memory_bytes(), 16 * 1024**3 * 40 // 100)

    def test_unparseable_memory_fails_closed(self):
        with mock.patch.object(MODULE, "command_output", return_value=""):
            self.assertEqual(MODULE.available_memory_bytes(), 0)

    def test_optional_content_markers_cover_surface_quality_dependencies(self):
        markers = MODULE.metahuman_optional_content_markers(Path("/engine/UE_5.8"))
        self.assertEqual(set(markers), {
            "textureSynthesis", "skinMicrotiling", "templateAnimations",
        })
        self.assertTrue(str(markers["skinMicrotiling"]).endswith(
            "Content/Optional/BodyTextures/T_Skin_Microtiling_M.uasset"
        ))


if __name__ == "__main__":
    unittest.main()
