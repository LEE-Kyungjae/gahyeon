#!/usr/bin/env python3

import importlib.util
from pathlib import Path
import unittest


TOOLS = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("coverage", TOOLS / "report_reference_coverage.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class CoverageTest(unittest.TestCase):
    def test_current_sources_do_not_fabricate_angles_or_expressions(self):
        pipeline = TOOLS.parent
        repository = pipeline.parent
        value = MODULE.report(
            repository / "artifacts/gahyeon-ch/identity-reference.json",
            pipeline / "reference/reference_requirements.json",
        )
        self.assertEqual(value["status"], "incomplete")
        self.assertEqual(value["coveredCounts"]["face"], 5)
        self.assertEqual(value["coveredCounts"]["body"], 2)
        self.assertEqual(value["coveredCounts"]["expressions"], 0)
        self.assertIn("left-45", value["missing"]["face"])
        self.assertIn("back", value["missing"]["body"])
        self.assertIn("viseme-aa", value["missing"]["expressions"])


if __name__ == "__main__":
    unittest.main()
