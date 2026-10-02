import copy
import json
import tempfile
import unittest
from pathlib import Path

from character_pipeline.evaluation.validate_reconstruction_benchmark import (
    validate_reconstruction_benchmark,
)


ROOT = Path(__file__).resolve().parents[1]


class ReconstructionBenchmarkValidationTest(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / "config/reconstruction_benchmark.json").read_text())
        self.status = json.loads((ROOT / "iterations/v001/generation/benchmark-status.json").read_text())

    def test_pending_status_is_truthful(self):
        result = validate_reconstruction_benchmark(
            self.config, self.status, ROOT / "iterations/v001/generation"
        )
        self.assertEqual(result["completedCandidates"], 0)
        self.assertFalse(result["selection"])

    def _complete_fixture(self, base: Path):
        status = copy.deepcopy(self.status)
        status["state"] = "validated"
        for model in ("trellis", "instantmesh"):
            record = status["models"][model]
            record.update({
                "runner": f"{model}-runner",
                "repository": f"https://example.invalid/{model}",
                "revision": "a" * 40,
                "weightsSha256": "b" * 64,
                "licenseReviewed": True,
            })
            for seed in self.config["seedSet"]:
                outputs = {}
                for role in self.config["requiredOutputs"]:
                    relative = Path(model) / str(seed) / f"{role}.artifact"
                    target = base / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(b"verified fixture")
                    outputs[role] = relative.as_posix()
                record["candidates"].append({
                    "seed": seed,
                    "status": "validated",
                    "claim": "temporary-shape-estimate-not-production-mesh",
                    "outputs": outputs,
                })
        return status

    def test_complete_two_model_three_seed_fixture_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            status = self._complete_fixture(base)
            result = validate_reconstruction_benchmark(self.config, status, base)
            self.assertEqual(result["completedCandidates"], 6)

    def test_missing_seed_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            status = self._complete_fixture(base)
            status["models"]["instantmesh"]["candidates"].pop()
            with self.assertRaisesRegex(ValueError, "seeds differ"):
                validate_reconstruction_benchmark(self.config, status, base)

    def test_unpinned_provenance_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            status = self._complete_fixture(base)
            status["models"]["trellis"]["revision"] = None
            with self.assertRaisesRegex(ValueError, "pinned provenance"):
                validate_reconstruction_benchmark(self.config, status, base)

    def test_early_selection_fails(self):
        status = copy.deepcopy(self.status)
        status["selection"] = {
            "model": "trellis", "seed": self.config["seedSet"][0],
            "role": "shape-reference-only", "automatic": False,
            "measurementEvidence": "pending", "humanReview": "pending",
        }
        with self.assertRaisesRegex(ValueError, "forbidden"):
            validate_reconstruction_benchmark(
                self.config, status, ROOT / "iterations/v001/generation"
            )

    def test_automatic_or_production_selection_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            status = self._complete_fixture(base)
            status["selection"] = {
                "model": "trellis", "seed": self.config["seedSet"][0],
                "role": "production-mesh", "automatic": True,
                "measurementEvidence": "report.json", "humanReview": "review.json",
            }
            with self.assertRaisesRegex(ValueError, "production role"):
                validate_reconstruction_benchmark(self.config, status, base)


if __name__ == "__main__":
    unittest.main()
