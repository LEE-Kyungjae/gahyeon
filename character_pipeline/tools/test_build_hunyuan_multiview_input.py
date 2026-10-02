#!/usr/bin/env python3

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from build_hunyuan_multiview_input import build_hunyuan_multiview_package


class HunyuanMultiviewInputTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        references = []
        for index, view in ((3, "front"), (7, "left-profile"), (8, "right-profile")):
            path = self.root / f"source-{index}.png"
            Image.new("RGB", (64 + index, 80), (index, 20, 30)).save(path)
            references.append({
                "index": index, "file": path.name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "view": view, "identityAuthority": "canonical",
            })
        self.identity = self.root / "identity.json"
        self.identity.write_text(json.dumps({
            "characterId": "test", "references": references,
        }))

    def tearDown(self):
        self.temp.cleanup()

    def test_builds_three_views_and_refuses_fake_back(self):
        output = self.root / "package"
        result = build_hunyuan_multiview_package(self.identity, self.root, output, 512)
        self.assertEqual(set(result["views"]), {"front", "left", "right"})
        self.assertEqual(result["missingViews"], ["back"])
        self.assertFalse(result["productionMeshAllowed"])
        self.assertFalse((output / "back.png").exists())
        with Image.open(output / "front.png") as image:
            self.assertEqual(image.size, (512, 512))

    def test_checksum_mismatch_fails_without_partial_package(self):
        content = json.loads(self.identity.read_text())
        content["references"][0]["sha256"] = "0" * 64
        self.identity.write_text(json.dumps(content))
        output = self.root / "package"
        with self.assertRaisesRegex(ValueError, "checksum differs"):
            build_hunyuan_multiview_package(self.identity, self.root, output, 512)
        self.assertFalse(output.exists())

    def test_refuses_overwrite(self):
        output = self.root / "package"
        output.mkdir()
        with self.assertRaisesRegex(FileExistsError, "refusing to overwrite"):
            build_hunyuan_multiview_package(self.identity, self.root, output, 512)


if __name__ == "__main__":
    unittest.main()
