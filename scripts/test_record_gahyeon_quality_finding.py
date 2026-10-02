#!/usr/bin/env python3

import json
import tempfile
import unittest
from pathlib import Path

import jsonschema

from create_gahyeon_quality_review import create
from gahyeon_quality_test_fixture import write_source_pack
from record_gahyeon_quality_finding import add_finding, disposition_finding


class RecordQualityFindingTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        identity, modeling = write_source_pack(self.root)
        self.review = self.root / "g1-review.json"
        create("G1", self.review, identity=identity, modeling=modeling)

    def tearDown(self):
        self.temp.cleanup()

    def test_assigns_monotonic_ids_and_trims_summary(self):
        first = add_finding(self.review, severity="major", summary="  fix profile  ")
        second = add_finding(self.review, severity="minor", summary="fix roughness")
        self.assertEqual("G1-001", first["id"])
        self.assertEqual("fix profile", first["summary"])
        self.assertEqual("G1-002", second["id"])

    def test_explicit_wrong_or_duplicate_id_is_atomic(self):
        add_finding(self.review, severity="note", summary="note", finding_id="G1-007")
        before = self.review.read_bytes()
        with self.assertRaisesRegex(ValueError, "already contains"):
            add_finding(self.review, severity="note", summary="again", finding_id="G1-007")
        self.assertEqual(before, self.review.read_bytes())
        with self.assertRaises(jsonschema.ValidationError):
            add_finding(self.review, severity="note", summary="wrong", finding_id="G2-001")
        self.assertEqual(before, self.review.read_bytes())

    def test_disposition_rules(self):
        add_finding(self.review, severity="blocking", summary="identity mismatch")
        before = self.review.read_bytes()
        with self.assertRaisesRegex(ValueError, "must be resolved"):
            disposition_finding(self.review, finding_id="G1-001", status="accepted-risk")
        self.assertEqual(before, self.review.read_bytes())
        item = disposition_finding(self.review, finding_id="G1-001", status="resolved")
        self.assertEqual("resolved", item["status"])
        with self.assertRaisesRegex(ValueError, "already resolved"):
            disposition_finding(self.review, finding_id="G1-001", status="resolved")

    def test_nonblocking_risk_acceptance_is_allowed(self):
        add_finding(self.review, severity="minor", summary="known compromise")
        item = disposition_finding(self.review, finding_id="G1-001", status="accepted-risk")
        self.assertEqual("accepted-risk", item["status"])

    def test_final_review_and_symlink_are_immutable(self):
        payload = json.loads(self.review.read_text())
        payload["status"] = "rejected"
        payload["findings"] = [{"id": "G1-001", "severity": "major",
                                "summary": "reject", "status": "open"}]
        self.review.write_text(json.dumps(payload))
        with self.assertRaisesRegex(ValueError, "draft or candidate"):
            add_finding(self.review, severity="note", summary="late")
        link = self.root / "link.json"
        link.symlink_to(self.review)
        with self.assertRaisesRegex(ValueError, "symbolic link"):
            add_finding(link, severity="note", summary="late")


if __name__ == "__main__":
    unittest.main()
