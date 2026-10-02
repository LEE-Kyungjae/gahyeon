import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from character_pipeline.tools.build_metahuman_conform_v002 import build, verify


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


class ConformV002Test(unittest.TestCase):
    def evidence(self, root, decision="keep-for-conform"):
        receipt = root / "import.json"; receipt.write_text(json.dumps({"state": "shape-imported-awaiting-guided-identity"}))
        items = []
        for view, kind in (("front", "viewport-screenshot"), ("left-profile", "viewport-screenshot"),
                           ("right-profile", "viewport-screenshot"), ("template-a", "identity-template-overlay"),
                           ("template-b", "identity-template-overlay")):
            p = root / f"{view}.png"; p.write_bytes(b"\x89PNG\r\n\x1a\nfixture")
            items.append({"view": view, "captureType": kind, "uri": p.name, "sha256": sha(p)})
        value = {"schemaVersion": 1, "sessionId": "gahyeon-metahuman-identity-v002",
                 "state": "identity-solved-human-reviewed", "automatic": False,
                 "productionReady": False, "qualityClaim": None,
                 "importReceipt": {"uri": receipt.name, "sha256": sha(receipt)},
                 "identityAsset": {"path": "/Game/Gahyeon/MHI_v002", "class": "MetaHumanIdentity"},
                 "reviewer": {"name": "Owner", "role": "character-owner"},
                 "reviewedAt": datetime.now(timezone.utc).isoformat(),
                 "checks": {k: True for k in ("componentsConfiguredFromMesh", "neutralFramePromoted",
                    "neutralFrameTracked", "markersHumanCorrected", "identitySolveCompleted",
                    "templateOverlayReviewed", "frontIdentityReviewed", "bothProfilesReviewed")},
                 "evidence": items, "canonicalComparison": {"referenceIndices": [3, 6, 7, 8],
                    "identityDecision": decision, "identityScore": None},
                 "blockingFindings": [] if decision == "keep-for-conform" else ["identity mismatch"]}
        path = root / "solve.json"; path.write_text(json.dumps(value)); return path

    def test_keep_builds_and_verifies(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); evidence = self.evidence(root)
            value = build(evidence, "/Game/Gahyeon/MHC_v002")
            job = root / "job.json"; job.write_text(json.dumps(value))
            self.assertEqual(verify(job)["requiredResult"], "SUCCESS")

    def test_reject_cannot_build(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            with self.assertRaisesRegex(ValueError, "does not allow"):
                build(self.evidence(root, "reject-and-resolve"), "/Game/Gahyeon/MHC")

    def test_job_evidence_drift_fails(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); evidence = self.evidence(root); value = build(evidence, "/Game/Gahyeon/MHC")
            job = root / "job.json"; job.write_text(json.dumps(value)); evidence.write_text("{}")
            with self.assertRaisesRegex(ValueError, "lineage"):
                verify(job)

    def test_wrong_params_fail(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); evidence = self.evidence(root); value = build(evidence, "/Game/Gahyeon/MHC")
            value["params"]["useEyeMeshes"] = False; job = root / "job.json"; job.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "parameters"):
                verify(job)

    def test_receipt_cannot_claim_downstream_quality(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); evidence = self.evidence(root); value = build(evidence, "/Game/Gahyeon/MHC")
            job = root / "job.json"; job.write_text(json.dumps(value))
            receipt = {"state": "conformed-head-awaiting-production-systems",
                       "job": {"path": str(job), "sha256": sha(job)}, "result": "SUCCESS", "headConformed": True,
                       **{key: False for key in ("faceRigGenerated", "highResolutionTexturesDownloaded", "bodyConformed",
                          "groomBound", "clothingBound", "deformationValidated", "lookingGlassGoValidated",
                          "automaticApproval", "productionReady")}, "qualityClaim": None}
            receipt["lookingGlassGoValidated"] = True; path = root / "receipt.json"; path.write_text(json.dumps(receipt))
            with self.assertRaisesRegex(ValueError, "overclaims"):
                verify(job, path)


if __name__ == "__main__": unittest.main()
