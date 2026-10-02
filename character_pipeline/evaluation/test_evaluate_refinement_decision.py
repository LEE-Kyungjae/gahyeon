#!/usr/bin/env python3

import copy
import json
import unittest
from pathlib import Path

from character_pipeline.evaluation.evaluate_refinement_decision import evaluate_refinement_decision


class RefinementDecisionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(Path("character_pipeline/config/refinement_decision.json").read_text())
        cls.baseline = json.loads(Path("character_pipeline/iterations/v001/evaluation/refinement-decision.json").read_text())

    def comparison(self, decision="keep"):
        return {
            "decision": decision, "parent": "v001",
            "hypothesis": "mouth is too narrow", "action": "widen mouth",
            "expectedResult": "identity improves", "actualResult": "identity changed",
            "rationale": "fixed camera comparison", "targetMetrics": ["identitySimilarity"],
            "guardrailMetrics": ["facialDeformation"],
            "comparisons": [
                {"metric": "identitySimilarity", "before": 80, "after": 82, "delta": 2},
                {"metric": "facialDeformation", "before": 85, "after": 85, "delta": 0},
            ],
            "blockingDefects": [], "automaticApproval": False,
        }

    def test_current_baseline(self):
        self.assertEqual(evaluate_refinement_decision(self.config, self.baseline)["decision"], "baseline")

    def test_keep_requires_target_improvement_and_guardrail(self):
        self.assertEqual(evaluate_refinement_decision(self.config, self.comparison())["decision"], "keep")

    def test_guardrail_regression_rejects(self):
        value = self.comparison("reject")
        value["comparisons"][1].update(after=84, delta=-1)
        self.assertTrue(evaluate_refinement_decision(self.config, value)["guardrailRegressed"])

    def test_blocking_defect_rejects(self):
        value = self.comparison("reject")
        value["blockingDefects"] = ["lip penetration"]
        self.assertEqual(evaluate_refinement_decision(self.config, value)["decision"], "reject")

    def test_unscored_is_inconclusive(self):
        value = self.comparison("inconclusive")
        value["comparisons"][0].update(before=None, after=None, delta=None)
        result = evaluate_refinement_decision(self.config, value)
        self.assertEqual(result["unscoredMetrics"], ["identitySimilarity"])

    def test_rejects_claimed_keep_when_guardrail_regresses(self):
        value = self.comparison("keep")
        value["comparisons"][1].update(after=84, delta=-1)
        with self.assertRaisesRegex(ValueError, "expected reject"):
            evaluate_refinement_decision(self.config, value)

    def test_rejects_false_delta(self):
        value = self.comparison()
        value["comparisons"][0]["delta"] = 5
        with self.assertRaisesRegex(ValueError, "declared delta"):
            evaluate_refinement_decision(self.config, value)


if __name__ == "__main__":
    unittest.main()
