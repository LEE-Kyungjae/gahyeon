#!/usr/bin/env python3

import json
import unittest
from pathlib import Path

from character_pipeline.tools.verify_deformation_diagnostics_scaffold import verify_deformation_diagnostics_scaffold


class DeformationDiagnosticsScaffoldTest(unittest.TestCase):
    def test_current_pending_scaffold(self):
        result = verify_deformation_diagnostics_scaffold(
            json.loads(Path("character_pipeline/config/deformation_diagnostics.json").read_text()),
            json.loads(Path("character_pipeline/config/deformation_qa.json").read_text()),
            json.loads(Path("character_pipeline/metahuman/validation/v001/deformation-diagnostics.json").read_text()),
        )
        self.assertEqual(result["frames"], 45)
        self.assertEqual(result["state"], "awaiting-editor-capture")


if __name__ == "__main__":
    unittest.main()
