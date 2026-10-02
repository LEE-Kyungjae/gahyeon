import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from authorize_metahuman_assembly import authorize


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AuthorizeMetaHumanAssemblyTest(unittest.TestCase):
    def fixture(self, root, decision_name="decision.json"):
        root = Path(root)
        solve = root / "solve.json"
        solve.write_text(json.dumps({
            "iteration": "v073", "result": "SUCCESS", "status": "draft",
            "productionReady": False, "identityApproved": False,
            "identityAsset": "/Game/Gahyeon/Identity/MHI_v073",
        }))
        job = root / "job.json"
        job.write_text(json.dumps({
            "state": "ready-for-head-only-identity-capture",
            "views": ["face-front", "face-left-45", "face-right-45", "face-left-profile", "face-right-profile"],
            "identityAsset": "/Game/Gahyeon/Identity/MHI_v073",
            "solveReceipt": {"sha256": digest(solve)},
        }))
        renders = []
        views = ["face-front", "face-left-45", "face-right-45", "face-left-profile", "face-right-profile"]
        for view in views:
            image = root / f"{view}.png"
            Image.new("RGB", (1440, 2560), "gray").save(image)
            renders.append({"view": view, "uri": image.name, "sha256": digest(image),
                            "camera": {"actorPath": "/Game/Cam", "location": [0, 0, 0],
                                       "rotation": [0, 0, 0], "focalLengthMm": 85}})
        capture = root / "capture.json"
        capture.write_text(json.dumps({
            "jobId": "gahyeon-post-conform-identity-v002", "profile": "looking-glass-go",
            "resolution": [1440, 2560], "background": "neutral-mid-gray", "qualityClaim": None,
            "editorRuntimeVerified": True, "headOnlyCheckpoint": True,
            "job": {"path": str(job), "sha256": digest(job)}, "renders": renders,
        }))
        decision = root / decision_name
        decision.write_text(json.dumps({
            "state": "post-conform-identity-human-reviewed", "reviewedIteration": "v073",
            "captureManifest": {"uri": capture.name, "sha256": digest(capture)},
            "reviewer": {"name": "owner", "role": "character-owner"},
            "comparison": {"canonicalIndices": [3, 6, 7, 8],
                           "decision": "keep-and-build-surfaces", "identityScore": None},
            "blockingFindings": [],
        }))
        return solve, decision

    def test_authorizes_bound_human_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            solve, decision = self.fixture(tmp)
            output = Path(tmp) / "authorization.json"
            result = authorize(decision, solve, output)
            self.assertEqual("metahuman-assembly-authorized", result["state"])
            self.assertEqual(5, result["verifiedViews"])
            self.assertFalse(result["automaticApproval"])

    def test_rejected_decision_blocks_assembly(self):
        with tempfile.TemporaryDirectory() as tmp:
            solve, decision = self.fixture(tmp)
            data = json.loads(decision.read_text())
            data["comparison"]["decision"] = "reject-and-resolve-identity"
            data["blockingFindings"] = ["identity mismatch"]
            decision.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "rejected assembly"):
                authorize(decision, solve, Path(tmp) / "authorization.json")

    def test_mismatched_solve_lineage_blocks_assembly(self):
        with tempfile.TemporaryDirectory() as tmp:
            solve, decision = self.fixture(tmp)
            data = json.loads(solve.read_text())
            data["identityAsset"] = "/Game/Gahyeon/Identity/OTHER"
            solve.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "not bound"):
                authorize(decision, solve, Path(tmp) / "authorization.json")


if __name__ == "__main__":
    unittest.main()
