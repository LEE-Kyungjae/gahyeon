import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from character_pipeline.tools.metahuman_identity_session_contract import (
    build_receipt, validate_import, verify_receipt,
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SessionContractTest(unittest.TestCase):
    def fixture(self, root):
        source = root / "head.obj"; source.write_text("o head\n")
        handoff = root / "handoff.json"; handoff.write_text("{}")
        preflight = root / "preflight.json"
        checks = {key: True for key in (
            "engineInstalled", "engineVersionSupported", "editorPresent",
            "metaHumanCoreDataPresent", "allRequiredPluginsPresent",
            "identityInputVerifiedShape", "immutableHandoffVerified",
            "minimumMemory", "minimumRuntimeFreeDiskHeadroom",
        )}
        preflight.write_text(json.dumps({"readyToLaunchIdentitySolve": True, "checks": checks}))
        session = root / "session.json"
        value = {
            "sessionId": "gahyeon-metahuman-identity-v002", "state": "ready-to-launch",
            "qualityClaim": None, "blockedChecks": [],
            "handoff": {"path": str(handoff), "sha256": sha(handoff)},
            "preflight": {"path": str(preflight), "sha256": sha(preflight)},
            "source": {"path": str(source), "sha256": sha(source), "claim": "neutral-static-mesh-input-not-metahuman-not-dna"},
            "unreal": {"replaceExisting": False},
        }
        session.write_text(json.dumps(value))
        return session, value, preflight

    def test_ready_fixture_builds_and_verifies_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); session_path, session, _ = self.fixture(root)
            loaded, source = validate_import(session_path)
            self.assertEqual(source.suffix, ".obj")
            receipt = root / "receipt.json"
            receipt.write_text(json.dumps(build_receipt(session_path, loaded, "/Game/Test/Shape")))
            self.assertTrue(verify_receipt(session_path, receipt)["valid"])

    def test_blocked_session_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); session_path, value, _ = self.fixture(root)
            value["state"] = "blocked-before-launch"; session_path.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "not ready"):
                validate_import(session_path)

    def test_preflight_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); session_path, _, preflight = self.fixture(root)
            preflight.write_text("{}")
            with self.assertRaisesRegex(ValueError, "preflight"):
                validate_import(session_path)

    def test_receipt_cannot_claim_solved_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); session_path, session, _ = self.fixture(root)
            receipt = root / "receipt.json"
            value = build_receipt(session_path, session, "/Game/Test/Shape")
            value["identitySolved"] = True; receipt.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "overclaims"):
                verify_receipt(session_path, receipt)


if __name__ == "__main__":
    unittest.main()
