#!/usr/bin/env python3

import hashlib
import tempfile
import unittest
from pathlib import Path

from character_pipeline.tools.verify_expression_ground_truth import validate_expression_ground_truth


class ExpressionGroundTruthTest(unittest.TestCase):
    def contract(self, root: Path) -> dict:
        source = root / "neutral.png"
        source.write_bytes(b"source")
        requirements = ["neutral"] + [f"missing-{index}" for index in range(15)]
        return {
            "status": "incomplete", "requirements": requirements,
            "authorityPolicy": {"landmarkMetricsAreEvidenceNotLabels": True},
            "displayQA": {"profile": "looking-glass-go", "singleViewResolution": [1440, 2560],
                          "quiltRequiresConnectedCalibration": True},
            "observations": [{"label": "neutral", "file": source.name,
                              "sha256": hashlib.sha256(b"source").hexdigest(),
                              "authority": "canonical", "humanObservation": "neutral",
                              "allowedUses": ["expression-baseline"]}],
            "missing": requirements[1:],
        }

    def test_valid_incomplete_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(validate_expression_ground_truth(self.contract(root), root)["covered"], 1)

    def test_rejects_fabricated_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            contract = self.contract(root)
            contract["missing"] = []
            with self.assertRaisesRegex(ValueError, "exactly complement"):
                validate_expression_ground_truth(contract, root)

    def test_rejects_wrong_display(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            contract = self.contract(root)
            contract["displayQA"]["singleViewResolution"] = [1920, 1080]
            with self.assertRaisesRegex(ValueError, "Looking Glass Go"):
                validate_expression_ground_truth(contract, root)


if __name__ == "__main__":
    unittest.main()
