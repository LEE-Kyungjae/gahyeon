#!/usr/bin/env python3

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("preflight_gahyeon_metahuman_toolchain.py")
SPEC = importlib.util.spec_from_file_location("metahuman_preflight", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class MetaHumanPreflightTest(unittest.TestCase):
    def test_engine_version_requires_parseable_5_6_or_newer(self):
        self.assertEqual(MODULE.engine_version(Path("/tmp/UE_5.6")), (5, 6))
        self.assertEqual(MODULE.engine_version(Path("/tmp/UE_5.7")), (5, 7))
        self.assertEqual(MODULE.engine_version(Path("/tmp/UE_5.8")), (5, 8))
        self.assertEqual(MODULE.engine_version(Path("/tmp/UE_5.5")), (5, 5))
        self.assertIsNone(MODULE.engine_version(Path("/tmp/Unreal")))

    def test_ue_5_8_plugin_names_are_supported(self):
        self.assertIn("MetaHumanCharacter", MODULE.PLUGIN_CANDIDATES["MetaHumanCreator"])
        self.assertIn("MetaHuman", MODULE.PLUGIN_CANDIDATES["MetaHumanAnimator"])
        self.assertIn(
            "MetaHumanCalibrationProcessing",
            MODULE.PLUGIN_CANDIDATES["MetaHumanAnimatorDepthProcessing"],
        )

    def test_plugin_lookup_uses_prebuilt_index(self):
        index = {"MetaHumanCharacter": "/engine/MetaHumanCharacter.uplugin"}
        self.assertEqual(
            MODULE.locate_plugin(
                Path("/missing-engine"),
                MODULE.PLUGIN_CANDIDATES["MetaHumanCreator"],
                index,
            ),
            "/engine/MetaHumanCharacter.uplugin",
        )

    def test_core_data_requires_all_ue_5_8_runtime_markers(self):
        with tempfile.TemporaryDirectory() as directory:
            engine = Path(directory)
            markers = (
                engine / "Engine/Plugins/MetaHuman/MetaHumanAnimator/Content/MeshFitting/Mesh2MetaHuman.uasset",
                engine / "Engine/Plugins/MetaHuman/MetaHumanSDK/Content/TemplateAssets/SM_MH_Head.uasset",
                engine / "Engine/Plugins/MetaHuman/MetaHumanCharacter/Content",
            )
            for marker in markers:
                if marker.suffix:
                    marker.parent.mkdir(parents=True, exist_ok=True)
                    marker.touch()
                else:
                    marker.mkdir(parents=True, exist_ok=True)
            self.assertEqual(len(MODULE.metahuman_core_data_markers(engine)), 3)
            markers[0].unlink()
            self.assertEqual(len(MODULE.metahuman_core_data_markers(engine)), 2)

    def test_handoff_verification_fails_closed_when_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid, detail = MODULE.verify_handoff(root, root / "missing.json")
        self.assertFalse(valid)
        self.assertIn("missing", detail)

    def test_current_v002_handoff_is_verified(self):
        root = SCRIPT.parent.parent
        handoff = root / "character_pipeline/metahuman/identity/v002/handoff.json"
        valid, detail = MODULE.verify_handoff(root, handoff)
        self.assertTrue(valid, detail)

    def test_runtime_disk_gate_is_lower_than_install_disk_gate(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"minimumFreeDiskHeadroom": free_bytes >= 80 * 1024**3', source)
        self.assertIn('"minimumRuntimeFreeDiskHeadroom": free_bytes >= 20 * 1024**3', source)
        self.assertIn('checks["minimumMemory"], checks["minimumRuntimeFreeDiskHeadroom"]', source)


if __name__ == "__main__":
    unittest.main()
