#!/usr/bin/env python3

import json
import tempfile
import unittest
from pathlib import Path

import jsonschema

from create_gahyeon_quality_review import create
from gahyeon_quality_test_fixture import write_source_pack
from record_gahyeon_quality_evidence import record
from verify_gahyeon_g1_review import verify as verify_g1


class RecordQualityEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        identity, modeling = write_source_pack(self.root)
        self.review = self.root / "g1-review.json"
        create("G1", self.review, identity=identity, modeling=modeling)
        self.capture = self.root / "captures/face-front.png"
        self.capture.parent.mkdir()
        self.capture.write_bytes(b"face-front")

    def tearDown(self):
        self.temp.cleanup()

    def test_records_checksum_and_nested_relative_uri(self):
        item = record(self.review, view="face-neutral-front",
                      capture_type="viewport-render", evidence_file=self.capture,
                      authority="canonical-observed")
        self.assertEqual("captures/face-front.png", item["uri"])
        result = verify_g1(self.review)
        self.assertEqual(1, result["evidenceCount"])
        self.assertEqual(14, len(result["missingRequiredViews"]))

    def test_duplicate_view_does_not_modify_review(self):
        record(self.review, view="face-neutral-front",
               capture_type="viewport-render", evidence_file=self.capture,
               authority="canonical-observed")
        before = self.review.read_bytes()
        with self.assertRaisesRegex(ValueError, "already contains"):
            record(self.review, view="face-neutral-front",
                   capture_type="wireframe", evidence_file=self.capture,
                   authority="canonical-observed")
        self.assertEqual(before, self.review.read_bytes())

    def test_wrong_capture_or_authority_fails_atomically(self):
        before = self.review.read_bytes()
        with self.assertRaises(jsonschema.ValidationError):
            record(self.review, view="face-neutral-front", capture_type="audio",
                   evidence_file=self.capture, authority="canonical-observed")
        self.assertEqual(before, self.review.read_bytes())
        with self.assertRaisesRegex(ValueError, "requires --authority"):
            record(self.review, view="face-neutral-front",
                   capture_type="viewport-render", evidence_file=self.capture)

    def test_outside_or_symlink_evidence_is_rejected(self):
        outside = self.root.parent / "outside-quality-evidence.png"
        outside.write_bytes(b"outside")
        link = self.root / "linked.png"
        try:
            with self.assertRaisesRegex(ValueError, "inside the review workspace"):
                record(self.review, view="face-neutral-front",
                       capture_type="viewport-render", evidence_file=outside,
                       authority="canonical-observed")
            link.symlink_to(self.capture)
            with self.assertRaisesRegex(ValueError, "symbolic link"):
                record(self.review, view="face-neutral-front",
                       capture_type="viewport-render", evidence_file=link,
                       authority="canonical-observed")
        finally:
            outside.unlink(missing_ok=True)

    def test_approved_or_rejected_review_is_immutable(self):
        payload = json.loads(self.review.read_text())
        for status in ("approved", "rejected"):
            payload["status"] = status
            self.review.write_text(json.dumps(payload))
            with self.assertRaisesRegex(ValueError, "cannot modify"):
                record(self.review, view="face-neutral-front",
                       capture_type="viewport-render", evidence_file=self.capture,
                       authority="canonical-observed")

    def test_g3_accepts_no_authority_and_rejects_one(self):
        g2 = self.root / "g2-review.json"
        g3 = self.root / "g3-review.json"
        create("G2", g2, previous=self.review, allow_unapproved_predecessor=True)
        create("G3", g3, previous=g2, allow_unapproved_predecessor=True)
        capture = self.root / "captures/groom-front.png"
        capture.write_bytes(b"groom-front")
        item = record(g3, view="groom-front", capture_type="viewport-render",
                      evidence_file=capture)
        self.assertNotIn("authority", item)
        second = self.root / "captures/groom-side.png"
        second.write_bytes(b"groom-side")
        with self.assertRaisesRegex(ValueError, "does not accept"):
            record(g3, view="groom-side", capture_type="viewport-render",
                   evidence_file=second, authority="technical-implementation")


if __name__ == "__main__":
    unittest.main()
