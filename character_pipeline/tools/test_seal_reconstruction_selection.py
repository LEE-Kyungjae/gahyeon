import copy
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from character_pipeline.tools.seal_reconstruction_selection import seal_selection

CONFIG = json.loads(Path("character_pipeline/config/reconstruction_human_review.json").read_text())
NOW = datetime(2026, 8, 13, 3, 0, tzinfo=timezone.utc)


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


class SealReconstructionSelectionTest(unittest.TestCase):
    def fixture(self, root):
        candidate = root / "trellis/20260813"; raw = candidate / "raw/mesh.glb"
        raw.parent.mkdir(parents=True); raw.write_bytes(b"mesh")
        state = {"state": "completed", "productionMeshAllowed": False,
                 "commands": [{"id": "cleanup", "argv": ["blender", "--input", str(raw)]}]}
        state_path = candidate / "postprocess-state.json"; state_path.write_text(json.dumps(state))
        shortlist = {"state": "awaiting-human-review", "selection": None, "automaticSelection": False,
                     "productionMeshAllowed": False, "displayProfile": "looking-glass-go",
                     "panelResolution": [1440, 2560], "candidates": [{"candidate": str(candidate),
                     "model": "trellis", "seed": 20260813, "eligibleForHumanReview": True,
                     "productionMeshAllowed": False, "postprocessStateSha256": sha(state_path),
                     "measurementRank": 1}]}
        shortlist_path = root / "shortlist.json"; shortlist_path.write_text(json.dumps(shortlist))
        review = {"schemaVersion": 1, "shortlist": {"path": str(shortlist_path), "sha256": sha(shortlist_path)},
                  "automatic": False, "productionMeshAllowed": False,
                  "reviewer": {"name": "Owner", "role": "character-owner"},
                  "reviewedAt": "2026-08-13T02:00:00Z", "selectedCandidate": str(candidate),
                  "views": [{"view": view, "verdict": "acceptable-for-conform", "notes": "reviewed"}
                            for view in CONFIG["requiredViews"]],
                  "criteria": [{"criterion": criterion, "verdict": "acceptable-for-conform", "notes": "reviewed"}
                               for criterion in CONFIG["requiredCriteria"]]}
        review_path = root / "review.json"; review_path.write_text(json.dumps(review))
        return shortlist_path, review_path, candidate

    def test_named_complete_review_seals_shape_reference_only(self):
        with tempfile.TemporaryDirectory() as directory:
            shortlist, review, _ = self.fixture(Path(directory))
            result = seal_selection(CONFIG, shortlist, review, NOW)
            self.assertEqual(result["state"], "selection-reviewed")
            self.assertEqual((result["viewReviewCount"], result["criterionReviewCount"]), (9, 9))
            self.assertFalse(result["automatic"]); self.assertFalse(result["productionMeshAllowed"])

    def test_blocking_view_or_missing_criterion_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            shortlist, review, _ = self.fixture(Path(directory)); value = json.loads(review.read_text())
            value["views"][3]["verdict"] = "blocking"; review.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "blocking view"):
                seal_selection(CONFIG, shortlist, review, NOW)
            value["views"][3]["verdict"] = "acceptable-for-conform"; value["criteria"].pop()
            review.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "every required"):
                seal_selection(CONFIG, shortlist, review, NOW)

    def test_automatic_or_unauthorized_review_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            shortlist, review, _ = self.fixture(Path(directory)); value = json.loads(review.read_text())
            value["automatic"] = True; review.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "cannot be automatic"):
                seal_selection(CONFIG, shortlist, review, NOW)
            value["automatic"] = False; value["reviewer"]["role"] = "automation"
            review.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "authorized named"):
                seal_selection(CONFIG, shortlist, review, NOW)

    def test_shortlist_or_candidate_tamper_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            shortlist, review, candidate = self.fixture(Path(directory))
            shortlist.write_text(shortlist.read_text() + " ")
            with self.assertRaisesRegex(ValueError, "lineage differ"):
                seal_selection(CONFIG, shortlist, review, NOW)
            value = json.loads(review.read_text()); value["shortlist"]["sha256"] = sha(shortlist)
            review.write_text(json.dumps(value)); (candidate / "postprocess-state.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "changed after shortlist"):
                seal_selection(CONFIG, shortlist, review, NOW)

    def test_ineligible_candidate_or_future_review_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            shortlist, review, _ = self.fixture(Path(directory)); value = json.loads(shortlist.read_text())
            value["candidates"][0]["eligibleForHumanReview"] = False; shortlist.write_text(json.dumps(value))
            review_value = json.loads(review.read_text()); review_value["shortlist"]["sha256"] = sha(shortlist)
            review.write_text(json.dumps(review_value))
            with self.assertRaisesRegex(ValueError, "not eligible"):
                seal_selection(CONFIG, shortlist, review, NOW)


if __name__ == "__main__": unittest.main()
