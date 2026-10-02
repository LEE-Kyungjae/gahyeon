#!/usr/bin/env python3

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("report_gahyeon_g2_readiness.py")
SPEC = importlib.util.spec_from_file_location("g2_readiness", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class G2ReadinessTest(unittest.TestCase):
    def test_current_style_draft_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "character"
            workspace.mkdir()
            (workspace / "g1-review.json").write_text(json.dumps({
                "status": "draft", "evidence": [], "approvals": []
            }), encoding="utf-8")
            project = root / "stage.uproject"
            project.write_text(json.dumps({
                "EngineAssociation": "5.6",
                "Plugins": [{"Name": "ControlRig", "Enabled": True}],
            }), encoding="utf-8")

            report = MODULE.inspect(workspace, project)

            self.assertFalse(report["readyForFormalG2Candidate"])
            self.assertEqual(report["g1"]["evidenceCount"], 0)
            self.assertIn("HairStrands", report["unreal"]["missingProductionPlugins"])
            self.assertIn("high-poly-master", report["g2"]["missingArtifactRoles"])

    def test_complete_fixture_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "character"
            workspace.mkdir()
            (workspace / "g1-review.json").write_text(json.dumps({
                "status": "approved",
                "evidence": [{}] * 15,
                "approvals": [{}],
                "modelArtifact": {"format": "blend"},
            }), encoding="utf-8")
            (workspace / "g2-review.json").write_text(json.dumps({
                "status": "draft",
                "artifacts": [
                    {"role": "high-poly-master"},
                    {"role": "animation-mesh"},
                ],
            }), encoding="utf-8")
            project = root / "stage.uproject"
            project.write_text(json.dumps({
                "EngineAssociation": "5.6",
                "Plugins": [
                    {"Name": name, "Enabled": True}
                    for name in MODULE.REQUIRED_UNREAL_PLUGINS
                ],
            }), encoding="utf-8")

            report = MODULE.inspect(workspace, project)

            self.assertTrue(report["readyForFormalG2Candidate"])
            self.assertEqual(report["g2"]["missingArtifactRoles"], [])
            self.assertEqual(report["unreal"]["missingProductionPlugins"], [])


if __name__ == "__main__":
    unittest.main()
