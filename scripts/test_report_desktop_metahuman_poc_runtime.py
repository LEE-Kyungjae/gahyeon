#!/usr/bin/env python3

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("report_desktop_metahuman_poc_runtime.py")
SPEC = importlib.util.spec_from_file_location("desktop_metahuman_runtime", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class DesktopMetaHumanPocRuntimeTest(unittest.TestCase):
    def test_success_with_missing_optional_content_is_limited(self):
        report = MODULE.classify_runtime_log("\n".join((
            "Interchange start importing source [/tmp/Archetype.mhdna]",
            "Built Skeletal Mesh [19.06s] /Engine/Transient/FaceMesh_0.FaceMesh_0",
            "waiting (BodyMesh_1)",
            "MetaHuman Optional Content folder not found.",
            MODULE.OPEN_MARKER,
        )))
        self.assertEqual(report["state"], "opened-limited-mode")
        self.assertTrue(report["editorOpened"])
        self.assertTrue(report["faceSkeletalMeshBuilt"])
        self.assertFalse(report["optionalContentPresent"])
        self.assertFalse(report["aaaQualityClaim"])

    def test_full_feature_open_requires_no_optional_content_warning(self):
        report = MODULE.classify_runtime_log(
            "Loading texture synthesis model data from file /Optional/TextureSynthesis/compressed.ar\n"
            + MODULE.OPEN_MARKER
        )
        self.assertEqual(report["state"], "opened-full-feature-mode")
        self.assertTrue(report["optionalContentPresent"])
        self.assertTrue(report["textureSynthesisModelLoaded"])

    def test_optional_path_in_success_log_is_not_treated_as_missing(self):
        report = MODULE.classify_runtime_log(
            "loaded /MetaHumanCharacter/Optional/Animation/TemplateAnimations\n"
            + MODULE.OPEN_MARKER
        )
        self.assertEqual(report["state"], "opened-full-feature-mode")

    def test_fatal_failure_overrides_open_marker(self):
        report = MODULE.classify_runtime_log(MODULE.OPEN_MARKER + "\nFatal error: test")
        self.assertEqual(report["state"], "failed")
        self.assertEqual(report["fatalError"], "Fatal error:")

    def test_absent_marker_is_not_opened(self):
        report = MODULE.classify_runtime_log("ordinary editor startup")
        self.assertEqual(report["state"], "not-opened")
        self.assertFalse(report["editorOpened"])


if __name__ == "__main__":
    unittest.main()
