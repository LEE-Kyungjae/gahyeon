#!/usr/bin/env python3

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from verify_gahyeon_g1_authoring_work_order import DEFAULT, verify


class G1AuthoringWorkOrderTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        source_root = DEFAULT.parent
        for relative in ("identity-reference.json", "modeling-input.json",
                         "g1-authoring-work-order.json", "g1-drafts/drafts-manifest.json"):
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_root / relative, target)
        self.manifest = self.root / "g1-authoring-work-order.json"

    def tearDown(self):
        self.temp.cleanup()

    def mutate(self, callback):
        payload = json.loads(self.manifest.read_text())
        callback(payload)
        self.manifest.write_text(json.dumps(payload))

    def test_current_work_order_is_complete(self):
        self.assertEqual(15, verify(self.manifest)["requiredEvidence"])

    def test_source_change_is_rejected(self):
        (self.root / "modeling-input.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            verify(self.manifest)

    def test_missing_or_duplicate_view_is_rejected(self):
        self.mutate(lambda p: p["requiredEvidence"].pop())
        with self.assertRaisesRegex(ValueError, "every required review view"):
            verify(self.manifest)

    def test_hidden_view_cannot_claim_canonical_authority(self):
        def change(payload):
            item = next(item for item in payload["requiredEvidence"]
                        if item["view"] == "hair-top")
            item["designAuthority"] = "canonical-observed"
        self.mutate(change)
        with self.assertRaisesRegex(ValueError, "wrong design authority"):
            verify(self.manifest)


if __name__ == "__main__":
    unittest.main()
