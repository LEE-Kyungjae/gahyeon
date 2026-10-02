#!/usr/bin/env python3

import copy
import json
import unittest
from pathlib import Path

from character_pipeline.tools.verify_expression_capture_job import validate_expression_capture_job


class ExpressionCaptureJobTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.value = json.loads(Path("character_pipeline/reference/expression_capture_job.json").read_text())

    def test_real_job_is_valid_and_non_promoting(self):
        self.assertEqual(validate_expression_capture_job(self.value)["targets"], 13)

    def test_rejects_automatic_promotion(self):
        value = copy.deepcopy(self.value)
        value["outputPolicy"]["automaticPromotion"] = True
        with self.assertRaisesRegex(ValueError, "automatically"):
            validate_expression_capture_job(value)

    def test_rejects_missing_target(self):
        value = copy.deepcopy(self.value)
        value["targets"].pop()
        with self.assertRaisesRegex(ValueError, "incomplete"):
            validate_expression_capture_job(value)


if __name__ == "__main__":
    unittest.main()
