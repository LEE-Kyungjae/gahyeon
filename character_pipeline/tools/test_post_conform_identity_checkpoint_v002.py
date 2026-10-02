import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from character_pipeline.tools.post_conform_identity_checkpoint_v002 import (
    VIEWS, build_job, verify_capture, verify_decision,
)


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


class CheckpointTest(unittest.TestCase):
    def conform(self, root):
        path = root / "conform.json"
        path.write_text(json.dumps({"state": "conformed-head-awaiting-production-systems",
            "result": "SUCCESS", "headConformed": True, "productionReady": False,
            "qualityClaim": None, "characterAsset": {"path": "/Game/Gahyeon/MHC_v002"}}))
        return path

    def capture(self, root):
        renders = root / "renders"; renders.mkdir()
        job = root / "capture-job.json"
        job.write_text(json.dumps({"state": "ready-for-head-only-identity-capture", "views": list(VIEWS)}))
        entries = []
        for view in VIEWS:
            image = renders / f"{view}.png"; Image.new("RGB", (1440, 2560), "gray").save(image)
            entries.append({"view": view, "uri": image.name, "sha256": sha(image),
                "camera": {"actorPath": f"/Game/Test/{view}", "location": [0, 0, 0],
                           "rotation": [0, 0, 0], "focalLengthMm": 70}})
        manifest = renders / "render-manifest.json"
        manifest.write_text(json.dumps({"jobId": "gahyeon-post-conform-identity-v002",
            "editorRuntimeVerified": True, "headOnlyCheckpoint": True,
            "job": {"path": str(job), "sha256": sha(job)},
            "profile": "looking-glass-go", "resolution": [1440, 2560],
            "background": "neutral-mid-gray", "qualityClaim": None, "renders": entries}))
        return manifest

    def decision(self, root, outcome, findings):
        capture = self.capture(root); path = root / "decision.json"
        path.write_text(json.dumps({"state": "post-conform-identity-human-reviewed",
            "captureManifest": {"uri": "renders/render-manifest.json", "sha256": sha(capture)},
            "reviewer": {"name": "Owner", "role": "character-owner"},
            "comparison": {"canonicalIndices": [3, 6, 7, 8], "decision": outcome, "identityScore": None},
            "blockingFindings": findings, "qualityClaim": None}))
        return path

    def test_build_job_is_head_only(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); value = build_job(self.conform(root), root / "renders")
            self.assertFalse(value["requiresGroom"]); self.assertEqual(value["resolution"], [1440, 2560])

    def test_capture_verifies(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(verify_capture(self.capture(Path(d)))["views"], 5)

    def test_keep_allows_surface_work(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(verify_decision(self.decision(Path(d), "keep-and-build-surfaces", []))["surfaceWorkAllowed"])

    def test_reject_blocks_surface_work(self):
        with tempfile.TemporaryDirectory() as d:
            result = verify_decision(self.decision(Path(d), "reject-and-resolve-identity", ["jaw mismatch"]))
            self.assertFalse(result["surfaceWorkAllowed"])

    def test_wrong_resolution_fails(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); manifest = self.capture(root); data = json.loads(manifest.read_text())
            image = manifest.parent / data["renders"][0]["uri"]; Image.new("RGB", (1024, 1024)).save(image)
            data["renders"][0]["sha256"] = sha(image); manifest.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "resolution"):
                verify_capture(manifest)

    def test_keep_with_blocker_fails(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, "blocking"):
                verify_decision(self.decision(Path(d), "keep-and-build-surfaces", ["ugly face"]))

    def test_missing_camera_provenance_fails(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); manifest = self.capture(root); data = json.loads(manifest.read_text())
            data["renders"][0].pop("camera"); manifest.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "camera"):
                verify_capture(manifest)


if __name__ == "__main__": unittest.main()
