import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from character_pipeline.tools.build_metahuman_identity_session import build, verify


ROOT = Path(__file__).resolve().parents[2]
HANDOFF = ROOT / "character_pipeline/metahuman/identity/v002/handoff.json"
PREFLIGHT = ROOT / "artifacts/gahyeon-ch/metahuman-toolchain-preflight-v3.json"


class IdentitySessionTest(unittest.TestCase):
    def test_current_bundle_is_blocked_but_lineage_valid(self):
        value = build(ROOT, HANDOFF, PREFLIGHT)
        self.assertEqual(value["state"], "blocked-before-launch")
        self.assertIn("engineInstalled", value["blockedChecks"])
        self.assertEqual(value["capture"]["resolution"], [1440, 2560])
        self.assertEqual(len(value["guidedStages"]), 7)

    def test_built_bundle_verifies(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "session.json"
            output.write_text(json.dumps(build(ROOT, HANDOFF, PREFLIGHT)))
            self.assertTrue(verify(output)["valid"])

    def test_tampered_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "session.json"
            value = build(ROOT, HANDOFF, PREFLIGHT)
            value["source"]["sha256"] = "0" * 64
            output.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "source"):
                verify(output)

    def test_false_ready_state_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "session.json"
            value = deepcopy(build(ROOT, HANDOFF, PREFLIGHT))
            value["state"] = "ready-to-launch"
            output.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "contradicts"):
                verify(output)


if __name__ == "__main__":
    unittest.main()
