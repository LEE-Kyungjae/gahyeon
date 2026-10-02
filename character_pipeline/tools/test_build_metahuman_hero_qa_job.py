#!/usr/bin/env python3
import copy
import json
import tempfile
import unittest
from pathlib import Path

from character_pipeline.tools.build_metahuman_hero_qa_job import build, verify


class HeroQaJobTest(unittest.TestCase):
    def decision(self):
        return {"state": "post-conform-identity-human-reviewed",
                "reviewer": {"name": "Owner", "role": "character-owner"},
                "comparison": {"decision": "keep-and-build-surfaces"}, "blockingFindings": []}

    def test_builds_full_hero_qa_matrix(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); decision = root / "decision.json"; decision.write_text(json.dumps(self.decision()))
            config = Path("character_pipeline/config/deformation_qa.json")
            value = build(decision, config, root / "renders"); job = root / "job.json"; job.write_text(json.dumps(value))
            result = verify(job)
            self.assertEqual(result["frames"], 45); self.assertEqual(result["cameras"], 7)

    def test_reject_identity_cannot_start_surface_qa(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); value = self.decision(); value["comparison"]["decision"] = "reject-and-resolve-identity"
            decision = root / "decision.json"; decision.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "keep-and-build"):
                build(decision, Path("character_pipeline/config/deformation_qa.json"), root / "renders")

    def test_blocking_identity_findings_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); value = self.decision(); value["blockingFindings"] = ["jaw differs"]
            decision = root / "decision.json"; decision.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "keep-and-build"):
                build(decision, Path("character_pipeline/config/deformation_qa.json"), root / "renders")


if __name__ == "__main__":
    unittest.main()
