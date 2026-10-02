#!/usr/bin/env python3

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import report_gahyeon_character_pipeline as reporter
from create_gahyeon_quality_review import create
from gahyeon_quality_test_fixture import write_source_pack


class CharacterPipelineReportTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.identity, self.modeling = write_source_pack(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_templates_do_not_count_as_started(self):
        (self.root / "g1-review-template.json").write_text("{}")
        result = reporter.report(self.root)
        self.assertEqual("G1", result["activeGate"])
        self.assertEqual("not-started", result["gates"][0]["status"])
        self.assertTrue(result["gates"][0]["templateAvailable"])

    def test_draft_reports_exact_missing_evidence(self):
        create("G1", self.root / "g1-review.json",
               identity=self.identity, modeling=self.modeling)
        result = reporter.report(self.root)
        self.assertEqual("G1", result["activeGate"])
        self.assertEqual("draft", result["gates"][0]["status"])
        self.assertEqual(15, result["gates"][0]["missingEvidence"])
        self.assertFalse(result["authoring"]["hasCandidateModel"])

    def test_candidate_model_artifact_is_reported_without_approving_gate(self):
        model = self.root / "authoring/gahyeon-g1.fbx"
        model.parent.mkdir()
        model.write_bytes(b"candidate")

        result = reporter.report(self.root)

        self.assertTrue(result["authoring"]["hasCandidateModel"])
        self.assertEqual(1, result["authoring"]["candidateModelArtifactCount"])
        self.assertEqual(["authoring/gahyeon-g1.fbx"],
                         result["authoring"]["candidateModelArtifacts"])
        self.assertEqual("G1", result["activeGate"])

    def test_invalid_review_is_not_progress(self):
        create("G1", self.root / "g1-review.json",
               identity=self.identity, modeling=self.modeling)
        payload = json.loads((self.root / "g1-review.json").read_text())
        payload["sourceManifests"][0]["sha256"] = "0" * 64
        (self.root / "g1-review.json").write_text(json.dumps(payload))
        result = reporter.report(self.root)
        self.assertEqual("invalid", result["gates"][0]["status"])
        self.assertFalse(result["qualityChainApproved"])

    def test_approved_chain_without_package_stops_at_hero(self):
        for gate in reporter.VERIFIERS:
            (self.root / f"{gate.lower()}-review.json").write_text("{}")
        approved = {gate: (lambda _path, gate=gate: {
            "status": "approved", "evidenceCount": reporter.EXPECTED_MISSING[gate],
            "missingRequiredViews": []}) for gate in reporter.VERIFIERS}
        with mock.patch.object(reporter, "VERIFIERS", approved):
            result = reporter.report(self.root)
        self.assertTrue(result["qualityChainApproved"])
        self.assertEqual("HERO_PACKAGE", result["activeGate"])
        self.assertFalse(result["hero"]["ready"])


if __name__ == "__main__":
    unittest.main()
