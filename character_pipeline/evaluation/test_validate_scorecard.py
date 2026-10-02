#!/usr/bin/env python3

import copy
import json
import tempfile
import unittest
from pathlib import Path

from character_pipeline.evaluation.validate_scorecard import validate_evidence_scorecard


class EvidenceScorecardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(Path("character_pipeline/config/scorecard.json").read_text())
        cls.path = Path("character_pipeline/iterations/v001/evaluation/scorecard.json")
        cls.scorecard = json.loads(cls.path.read_text())

    def test_current_scorecard(self):
        result = validate_evidence_scorecard(self.config, self.scorecard, self.path.parent)
        self.assertEqual(result["components"], 13)
        self.assertEqual(result["measuredNotScored"], 3)
        self.assertEqual(result["unverified"], 10)
        self.assertIsNone(result["overall"])

    def test_rejects_number_on_unverified_component(self):
        value = copy.deepcopy(self.scorecard)
        value["components"]["skin"]["score"] = 50
        with self.assertRaisesRegex(ValueError, "carries a number"):
            validate_evidence_scorecard(self.config, value, self.path.parent)

    def test_rejects_fabricated_overall(self):
        value = copy.deepcopy(self.scorecard)
        value["overall"] = 45
        with self.assertRaisesRegex(ValueError, "overall score"):
            validate_evidence_scorecard(self.config, value, self.path.parent)

    def test_rejects_missing_evidence(self):
        value = copy.deepcopy(self.scorecard)
        value["components"]["eyes"]["evidence"] = ["does-not-exist.json"]
        with self.assertRaisesRegex(ValueError, "missing component evidence"):
            validate_evidence_scorecard(self.config, value, self.path.parent)

    def test_computes_overall_only_when_everything_is_scored_and_clear(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            value = copy.deepcopy(self.scorecard)
            import hashlib
            for name, record in value["components"].items():
                evidence = root / f"{name}.json"
                evidence.write_text(json.dumps({"component": name}))
                checksum = hashlib.sha256(evidence.read_bytes()).hexdigest()
                receipt = root / f"{name}-receipt.json"
                receipt.write_text(json.dumps({"valid": True, "component": name,
                    "iteration": "v001", "evidenceSha256": checksum,
                    "automaticApproval": False}))
                record["status"] = "scored"
                record["score"] = 80
                record["defects"] = []
                record["evidence"] = [{"uri": evidence.name, "sha256": checksum,
                                       "verifierReceipt": receipt.name}]
            value["overall"] = 80.0
            result = validate_evidence_scorecard(self.config, value, root)
            self.assertEqual(result["overall"], 80.0)

    def test_scored_component_rejects_legacy_path_only_evidence(self):
        value = copy.deepcopy(self.scorecard)
        record = value["components"]["identitySimilarity"]
        record["status"] = "scored"
        record["score"] = 80
        with self.assertRaisesRegex(ValueError, "lacks checksum"):
            validate_evidence_scorecard(self.config, value, self.path.parent)


if __name__ == "__main__":
    unittest.main()
