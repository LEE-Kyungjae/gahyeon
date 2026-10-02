import copy
import json
import tempfile
import unittest
from pathlib import Path

from character_pipeline.evaluation.build_reconstruction_shortlist import build_shortlist

CONFIG = json.loads(Path("character_pipeline/config/reconstruction_shortlist.json").read_text())


class ReconstructionShortlistTest(unittest.TestCase):
    def candidate(self, root, model, seed, error=10.0, valid=True):
        candidate = root / model / str(seed)
        evidence = candidate / "postprocess/evaluation"
        evidence.mkdir(parents=True)
        qualities = []
        for view in CONFIG["requiredViews"]:
            path = evidence / f"render-quality-{view}.json"
            path.write_text(json.dumps({"dimensions": [1440, 2560], "expectedDimensions": [1440, 2560],
                                        "validCapture": valid, "defects": [] if valid else ["too-dark"],
                                        "qualityClaim": None}))
            qualities.append(str(path))
        face = evidence / "face-comparison.json"; body = evidence / "body-comparison.json"
        face.write_text(json.dumps({"identitySimilarityScore": None, "deltas": [
            {"relativeDeltaPercent": error}, {"relativeDeltaPercent": -error / 2}]}))
        body.write_text(json.dumps({"bodySimilarityScore": None, "deltas": [
            {"relativeDeltaPercent": error * 1.5}, {"relativeDeltaPercent": -error}]}))
        state = {"state": "completed", "claim": "evaluated-temporary-shape-estimate-not-production-mesh",
                 "productionMeshAllowed": False, "panelResolution": [1440, 2560],
                 "views": CONFIG["requiredViews"], "model": model, "seed": seed,
                 "expected": {"renderQuality": qualities, "faceComparison": str(face), "bodyComparison": str(body)}}
        (candidate / "postprocess-state.json").write_text(json.dumps(state))
        return candidate

    def six(self, root):
        return [self.candidate(root, model, seed, error=5 + index)
                for index, (model, seed) in enumerate((
                    (model, seed) for model in CONFIG["models"] for seed in CONFIG["seeds"]
                ))]

    def test_six_candidates_rank_but_never_select(self):
        with tempfile.TemporaryDirectory() as directory:
            result = build_shortlist(CONFIG, self.six(Path(directory)))
            self.assertEqual([item["measurementRank"] for item in result["candidates"]], list(range(1, 7)))
            self.assertIsNone(result["selection"]); self.assertFalse(result["automaticSelection"])
            self.assertFalse(result["productionMeshAllowed"])

    def test_missing_candidate_or_duplicate_model_seed_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            candidates = self.six(Path(directory))
            with self.assertRaisesRegex(ValueError, "six distinct"):
                build_shortlist(CONFIG, candidates[:-1])
            state = json.loads((candidates[-1] / "postprocess-state.json").read_text())
            state["seed"] = CONFIG["seeds"][0]
            (candidates[-1] / "postprocess-state.json").write_text(json.dumps(state))
            with self.assertRaisesRegex(ValueError, "both models and all seeds"):
                build_shortlist(CONFIG, candidates)

    def test_bad_render_or_wrong_go_resolution_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            candidates = self.six(Path(directory))
            state = json.loads((candidates[0] / "postprocess-state.json").read_text())
            quality = Path(state["expected"]["renderQuality"][0])
            value = json.loads(quality.read_text()); value["dimensions"] = [1920, 1080]
            quality.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "not Looking Glass Go"):
                build_shortlist(CONFIG, candidates)

    def test_fabricated_similarity_score_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            candidates = self.six(Path(directory))
            state = json.loads((candidates[0] / "postprocess-state.json").read_text())
            face = Path(state["expected"]["faceComparison"])
            value = json.loads(face.read_text()); value["identitySimilarityScore"] = 99.9
            face.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "fabricates"):
                build_shortlist(CONFIG, candidates)

    def test_threshold_excludes_candidate_from_human_shortlist(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); candidates = self.six(root)
            state = json.loads((candidates[-1] / "postprocess-state.json").read_text())
            for key in ("faceComparison", "bodyComparison"):
                path = Path(state["expected"][key]); value = json.loads(path.read_text())
                for delta in value["deltas"]: delta["relativeDeltaPercent"] = 100
                path.write_text(json.dumps(value))
            result = build_shortlist(CONFIG, candidates)
            self.assertFalse(result["candidates"][-1]["eligibleForHumanReview"])
            self.assertEqual(len(result["shortlist"]), 5)


if __name__ == "__main__":
    unittest.main()
