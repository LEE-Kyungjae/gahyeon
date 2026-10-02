#!/usr/bin/env python3

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from build_gahyeon_blender_g1_scene_plan import build_plan
from package_gahyeon_g1_handoff import DEFAULT_INPUT, package


class BlenderG1ScenePlanTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        archive = self.root / "handoff.zip"
        package(DEFAULT_INPUT, archive)
        self.handoff = self.root / "handoff"
        with zipfile.ZipFile(archive) as source:
            source.extractall(self.handoff)

    def tearDown(self):
        self.temp.cleanup()

    def test_plan_has_all_references_but_only_canonical_geometry_anchors(self):
        plan = build_plan(self.handoff)
        self.assertEqual(15, len(plan["evidenceCameras"]))
        self.assertEqual(15, len({item["view"] for item in plan["evidenceCameras"]}))
        self.assertEqual(29, len(plan["referenceImages"]))
        classifications = [item["classification"] for item in plan["referenceImages"]]
        self.assertEqual(18, classifications.count("canonical"))
        self.assertEqual(11, classifications.count("supporting"))
        self.assertEqual(0.01, plan["scene"]["unitScale"])
        self.assertIn("G1_MODEL_HAIR", plan["scene"]["collections"])
        self.assertIn("G1_MODEL_OUTFIT", plan["scene"]["collections"])
        self.assertIn("G1_GUIDES_NON_AUTHORITATIVE", plan["scene"]["collections"])
        self.assertEqual("non-authoritative-adjustable",
                         plan["authoringGuides"]["authority"])
        self.assertEqual("X=0", plan["authoringGuides"]["symmetryPlane"])
        self.assertEqual([0, 0, 162], plan["authoringGuides"]["landmarksCm"]["eye_line"])
        cameras = {item["view"]: item for item in plan["evidenceCameras"]}
        self.assertEqual([0, -180, 160], cameras["face-neutral-front"]["locationCm"])
        self.assertEqual([0, 0, 160], cameras["face-neutral-front"]["targetCm"])
        self.assertEqual(60, cameras["face-neutral-front"]["orthoScaleCm"])
        self.assertEqual([0, 0, 300], cameras["hair-top"]["locationCm"])
        self.assertEqual(1024, plan["evidenceRender"]["resolutionX"])
        self.assertTrue(plan["evidenceRender"]["transparentBackground"])

    def test_changed_reference_is_rejected(self):
        plan = build_plan(self.handoff)
        target = self.handoff / plan["referenceImages"][0]["path"]
        target.write_bytes(target.read_bytes() + b"tamper")
        with self.assertRaisesRegex(ValueError, "integrity check"):
            build_plan(self.handoff)

    def test_supporting_reference_cannot_be_promoted_to_geometry_anchor(self):
        work_order = self.handoff / "g1-authoring-work-order.json"
        payload = json.loads(work_order.read_text(encoding="utf-8"))
        payload["requiredEvidence"][0]["sourceAnchors"] = [12]
        work_order.write_text(json.dumps(payload), encoding="utf-8")
        manifest = self.handoff / "package-manifest.json"
        inventory = json.loads(manifest.read_text(encoding="utf-8"))
        item = next(item for item in inventory["files"]
                    if item["path"] == "g1-authoring-work-order.json")
        import hashlib
        data = work_order.read_bytes()
        item["bytes"] = len(data)
        item["sha256"] = hashlib.sha256(data).hexdigest()
        manifest.write_text(json.dumps(inventory), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "supporting reference"):
            build_plan(self.handoff)


if __name__ == "__main__":
    unittest.main()
