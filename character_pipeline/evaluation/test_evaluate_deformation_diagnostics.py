#!/usr/bin/env python3

import copy
import json
import math
import unittest
from pathlib import Path

from character_pipeline.evaluation.evaluate_deformation_diagnostics import evaluate_deformation_diagnostics


class DeformationDiagnosticsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(Path("character_pipeline/config/deformation_diagnostics.json").read_text())
        cls.cases = json.loads(Path("character_pipeline/config/deformation_qa.json").read_text())

    def report(self):
        samples = []
        for case in self.cases["requiredCases"]:
            for frame in case["frames"]:
                diagnostics = {}
                for name, contract in self.config["diagnostics"].items():
                    value = 1.0 if name == "neckStretchRatio" else 0.0
                    diagnostics[name] = {"value": value, "unit": contract["unit"]}
                samples.append({"case": case["id"], "frame": frame, "diagnostics": diagnostics})
        return {"state": "candidate", "editorRuntimeVerified": True, "samples": samples,
                "summary": {"sampleCount": 45, "failedSampleCount": 0}, "qualityClaim": None}

    def test_complete_fixture(self):
        result = evaluate_deformation_diagnostics(self.config, self.cases, self.report())
        self.assertEqual(result["samples"], 45)
        self.assertEqual(result["diagnostics"], 11)

    def test_rejects_missing_frame(self):
        report = self.report()
        report["samples"].pop()
        report["summary"]["sampleCount"] = 44
        with self.assertRaisesRegex(ValueError, "coverage mismatch"):
            evaluate_deformation_diagnostics(self.config, self.cases, report)

    def test_rejects_wrong_unit(self):
        report = self.report()
        report["samples"][0]["diagnostics"]["lipPenetrationMm"]["unit"] = "cm"
        with self.assertRaisesRegex(ValueError, "unit mismatch"):
            evaluate_deformation_diagnostics(self.config, self.cases, report)

    def test_rejects_non_finite(self):
        report = self.report()
        report["samples"][0]["diagnostics"]["lipSealGapMm"]["value"] = math.nan
        with self.assertRaisesRegex(ValueError, "invalid diagnostic"):
            evaluate_deformation_diagnostics(self.config, self.cases, report)

    def test_rejects_threshold_failure(self):
        report = self.report()
        report["samples"][0]["diagnostics"]["meshClippingPairs"]["value"] = 1
        report["summary"]["failedSampleCount"] = 1
        with self.assertRaisesRegex(ValueError, "thresholds exceeded"):
            evaluate_deformation_diagnostics(self.config, self.cases, report)

    def test_rejects_false_summary(self):
        report = self.report()
        report["summary"]["sampleCount"] = 44
        with self.assertRaisesRegex(ValueError, "summary disagrees"):
            evaluate_deformation_diagnostics(self.config, self.cases, report)


if __name__ == "__main__":
    unittest.main()
