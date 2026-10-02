#!/usr/bin/env python3

import json
import tempfile
import unittest
from pathlib import Path

import jsonschema

from create_gahyeon_quality_review import create
from gahyeon_quality_test_fixture import write_source_pack
from record_gahyeon_quality_approval import approve
from record_gahyeon_quality_artifact import record as record_artifact
from record_gahyeon_quality_evidence import record as record_evidence
from transition_gahyeon_quality_review import transition
from verify_gahyeon_g1_review import ARTIST_REQUIRED, REQUIRED_VIEWS, verify


class QualityReviewLifecycleTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        identity, modeling = write_source_pack(self.root)
        self.review = self.root / "g1-review.json"
        create("G1", self.review, identity=identity, modeling=modeling)

    def tearDown(self):
        self.temp.cleanup()

    def complete_draft(self):
        model = self.root / "gahyeon.glb"
        model.write_bytes(b"model")
        record_artifact(self.review, artifact_file=model, artifact_format="glb")
        for index, view in enumerate(sorted(REQUIRED_VIEWS)):
            capture = self.root / f"evidence-{index}.png"
            capture.write_bytes(view.encode())
            record_evidence(
                self.review, view=view, capture_type="viewport-render",
                evidence_file=capture,
                authority=("artist-authored-completion" if view in ARTIST_REQUIRED
                           else "canonical-observed"))

    def test_incomplete_draft_cannot_become_candidate_atomically(self):
        before = self.review.read_bytes()
        with self.assertRaises(jsonschema.ValidationError):
            transition(self.review, "candidate")
        self.assertEqual(before, self.review.read_bytes())

    def test_complete_candidate_requires_all_approvals_for_approval(self):
        self.complete_draft()
        transition(self.review, "candidate")
        self.assertEqual("candidate", verify(self.review)["status"])
        before = self.review.read_bytes()
        with self.assertRaises(jsonschema.ValidationError):
            transition(self.review, "approved")
        self.assertEqual(before, self.review.read_bytes())
        for role in ("identity-reviewer", "technical-reviewer", "operator"):
            approve(self.review, role=role, reviewer=f"fixture-{role}",
                    approved_at="2026-08-12T00:00:00Z")
        transition(self.review, "approved")
        self.assertEqual("approved", verify(self.review, require_approved=True)["status"])

    def test_duplicate_or_draft_approval_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "only be recorded on a candidate"):
            approve(self.review, role="operator", reviewer="fixture")
        self.complete_draft()
        transition(self.review, "candidate")
        approve(self.review, role="operator", reviewer="fixture")
        before = self.review.read_bytes()
        with self.assertRaisesRegex(ValueError, "already contains"):
            approve(self.review, role="operator", reviewer="other")
        self.assertEqual(before, self.review.read_bytes())

    def test_blocking_finding_prevents_approval(self):
        self.complete_draft()
        transition(self.review, "candidate")
        payload = json.loads(self.review.read_text())
        payload["findings"] = [{"id": "G1-001", "severity": "blocking",
                                "summary": "identity mismatch", "status": "open"}]
        payload["approvals"] = [
            {"role": role, "reviewer": role, "approvedAt": "2026-08-12T00:00:00Z"}
            for role in ("identity-reviewer", "technical-reviewer", "operator")]
        self.review.write_text(json.dumps(payload))
        with self.assertRaisesRegex(ValueError, "blocking findings"):
            transition(self.review, "approved")

    def test_rejection_requires_finding_and_is_terminal(self):
        with self.assertRaisesRegex(ValueError, "documented finding"):
            transition(self.review, "rejected")
        payload = json.loads(self.review.read_text())
        payload["findings"] = [{"id": "G1-001", "severity": "major",
                                "summary": "revise proportions", "status": "open"}]
        self.review.write_text(json.dumps(payload))
        transition(self.review, "rejected")
        with self.assertRaisesRegex(ValueError, "not allowed"):
            transition(self.review, "candidate")


if __name__ == "__main__":
    unittest.main()
