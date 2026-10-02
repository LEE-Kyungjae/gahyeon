#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_gahyeon_identity_reference import verify
from gahyeon_quality_test_fixture import write_source_pack


class GahyeonIdentityReferenceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.pack, _ = write_source_pack(self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_fixture_pack_classifies_every_present_source(self) -> None:
        self.assertEqual((19, 12, 6), verify(self.pack))

    def test_unclassified_source_fails_closed(self) -> None:
        manifest = json.loads(self.pack.read_text(encoding="utf-8"))
        (self.root / "ChatGPT Image unclassified.png").write_bytes(b"unclassified")
        manifest["sourceInventory"]["operatorDeclaredCount"] = 20
        manifest["sourceInventory"]["presentCount"] = 20
        self.pack.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "classified exactly once"):
            verify(self.pack)

    def test_inventory_status_cannot_hide_a_count_discrepancy(self) -> None:
        manifest = json.loads(self.pack.read_text(encoding="utf-8"))
        manifest["sourceInventory"]["operatorDeclaredCount"] = 20
        manifest["sourceInventory"]["status"] = "complete"
        self.pack.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "status does not match"):
            verify(self.pack)


if __name__ == "__main__":
    unittest.main()
