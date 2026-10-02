#!/usr/bin/env python3
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from character_pipeline.evaluation.build_metahuman_identity_comparison_board import build, sha256, verify


class ComparisonBoardTest(unittest.TestCase):
    def fixtures(self, root: Path):
        refs = []
        for index, view in ((3, "front"), (6, "three-quarter"), (7, "left-profile"), (8, "right-profile")):
            path = root / f"ref-{index}.png"; Image.new("RGB", (80, 120), (index, 10, 20)).save(path)
            refs.append({"index": index, "file": path.name, "sha256": sha256(path), "view": view, "identityAuthority": "canonical"})
        identity = root / "identity.json"
        identity.write_text(json.dumps({"status": "source-canon", "canonicalSource": "user-provided-originals", "references": refs}))
        renders = []
        for view in ("face-front", "face-left-45", "face-right-45", "face-left-profile", "face-right-profile"):
            path = root / f"{view}.png"; Image.new("RGB", (1440, 2560), (30, 40, 50)).save(path)
            renders.append({"view": view, "uri": path.name, "sha256": sha256(path),
                            "camera": {"actorPath": "/Game/Cam", "location": [0, 0, 0], "rotation": [0, 0, 0], "focalLengthMm": 85}})
        capture = root / "capture.json"
        capture.write_text(json.dumps({"jobId": "gahyeon-post-conform-identity-v002", "editorRuntimeVerified": True,
                                       "resolution": [1440, 2560], "profile": "looking-glass-go", "renders": renders}))
        return identity, capture

    def test_builds_checksum_bound_five_view_board(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); identity, capture = self.fixtures(root)
            board, manifest = root / "board.jpg", root / "comparison.json"
            value = build(identity, capture, board); manifest.write_text(json.dumps(value))
            self.assertEqual(verify(manifest)["views"], 5)
            self.assertIsNone(value["identityScore"])

    def test_rejects_candidate_checksum_tampering(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); identity, capture = self.fixtures(root)
            value = json.loads(capture.read_text()); value["renders"][0]["sha256"] = "0" * 64
            capture.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "candidate checksum"):
                build(identity, capture, root / "board.jpg")


if __name__ == "__main__":
    unittest.main()
