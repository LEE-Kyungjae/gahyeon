import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from character_pipeline.evaluation.build_metahuman_recovery_board_v073 import build, sha256


class RecoveryBoardV073Test(unittest.TestCase):
    def test_builds_non_approving_five_view_board(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            refs = []
            for index, view in ((3, "front"), (6, "three-quarter"), (7, "left-profile"), (8, "right-profile")):
                path = root / f"canonical-{index}.png"
                Image.new("RGB", (80, 120), (index, 20, 30)).save(path)
                refs.append({"index": index, "file": path.name, "sha256": sha256(path),
                             "view": view, "identityAuthority": "canonical"})
            identity = root / "identity.json"
            identity.write_text(json.dumps({"status": "source-canon", "canonicalSource": "user-provided-originals",
                                            "references": refs}))
            renders = []
            for view in ("face-front", "face-left-45", "face-right-45", "face-left-profile", "face-right-profile"):
                path = root / f"{view}.png"
                Image.new("RGB", (1440, 2560), (40, 50, 60)).save(path)
                renders.append({"view": view, "uri": path.name, "sha256": sha256(path)})
            capture = root / "capture.json"
            capture.write_text(json.dumps({
                "jobId": "gahyeon-metahuman-template-baseline-v074",
                "state": "captured-sane-template-baseline", "editorRuntimeVerified": True,
                "resolution": [1440, 2560], "automaticApproval": False, "renders": renders,
            }))
            result = build(identity, capture, root / "board.jpg")
            self.assertEqual("sane-template-baseline-ready-for-defect-analysis", result["state"])
            self.assertIsNone(result["identityScore"])
            self.assertFalse(result["automaticApproval"])


if __name__ == "__main__":
    unittest.main()
