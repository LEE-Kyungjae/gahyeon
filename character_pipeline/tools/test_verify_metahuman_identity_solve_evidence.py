import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from character_pipeline.tools.verify_metahuman_identity_solve_evidence import verify


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


class SolveEvidenceTest(unittest.TestCase):
    def fixture(self, root, decision="keep-for-conform"):
        receipt = root / "receipt.json"
        receipt.write_text(json.dumps({"state": "shape-imported-awaiting-guided-identity"}))
        evidence = []
        for view, kind in (("front", "viewport-screenshot"), ("left-profile", "viewport-screenshot"),
                           ("right-profile", "viewport-screenshot"), ("template-a", "identity-template-overlay"),
                           ("template-b", "identity-template-overlay")):
            image = root / f"{view}.png"; image.write_bytes(b"\x89PNG\r\n\x1a\nfixture")
            evidence.append({"view": view, "captureType": kind, "uri": image.name, "sha256": sha(image)})
        value = {
            "schemaVersion": 1, "sessionId": "gahyeon-metahuman-identity-v002",
            "state": "identity-solved-human-reviewed", "automatic": False,
            "productionReady": False, "qualityClaim": None,
            "importReceipt": {"uri": receipt.name, "sha256": sha(receipt)},
            "identityAsset": {"path": "/Game/Gahyeon/MHI_v002", "class": "MetaHumanIdentity"},
            "reviewer": {"name": "Owner", "role": "character-owner"},
            "reviewedAt": datetime.now(timezone.utc).isoformat(),
            "checks": {key: True for key in (
                "componentsConfiguredFromMesh", "neutralFramePromoted", "neutralFrameTracked",
                "markersHumanCorrected", "identitySolveCompleted", "templateOverlayReviewed",
                "frontIdentityReviewed", "bothProfilesReviewed")},
            "evidence": evidence,
            "canonicalComparison": {"referenceIndices": [3, 6, 7, 8],
                                    "identityDecision": decision, "identityScore": None},
            "blockingFindings": [] if decision == "keep-for-conform" else ["jaw identity mismatch"],
        }
        path = root / "solve.json"; path.write_text(json.dumps(value)); return path, value

    def test_keep_allows_conform(self):
        with tempfile.TemporaryDirectory() as d:
            path, _ = self.fixture(Path(d)); self.assertTrue(verify(path)["conformAllowed"])

    def test_reject_is_valid_but_blocks_conform(self):
        with tempfile.TemporaryDirectory() as d:
            path, _ = self.fixture(Path(d), "reject-and-resolve"); self.assertFalse(verify(path)["conformAllowed"])

    def test_missing_profile_fails(self):
        with tempfile.TemporaryDirectory() as d:
            path, value = self.fixture(Path(d)); value["evidence"].pop(); path.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "exact front"):
                verify(path)

    def test_bot_reviewer_fails(self):
        with tempfile.TemporaryDirectory() as d:
            path, value = self.fixture(Path(d)); value["reviewer"]["role"] = "bot"; path.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "reviewer"):
                verify(path)

    def test_numeric_score_fails(self):
        with tempfile.TemporaryDirectory() as d:
            path, value = self.fixture(Path(d)); value["canonicalComparison"]["identityScore"] = 92.0; path.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "numeric"):
                verify(path)

    def test_blocking_finding_prevents_keep(self):
        with tempfile.TemporaryDirectory() as d:
            path, value = self.fixture(Path(d)); value["blockingFindings"] = ["ugly jaw"]; path.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "blocking"):
                verify(path)


if __name__ == "__main__": unittest.main()
