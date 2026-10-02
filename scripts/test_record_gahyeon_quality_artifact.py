#!/usr/bin/env python3

import json
import tempfile
import unittest
from pathlib import Path

import jsonschema

from create_gahyeon_quality_review import create
from gahyeon_quality_test_fixture import write_source_pack
from record_gahyeon_quality_artifact import record
from verify_gahyeon_g1_review import verify as verify_g1


class RecordQualityArtifactTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        identity, modeling = write_source_pack(self.root)
        self.g1 = self.root / "g1-review.json"
        create("G1", self.g1, identity=identity, modeling=modeling)
        self.model = self.root / "models/gahyeon.glb"
        self.model.parent.mkdir()
        self.model.write_bytes(b"g1-model")

    def tearDown(self):
        self.temp.cleanup()

    def test_records_g1_model_size_checksum_and_uri(self):
        item = record(self.g1, artifact_file=self.model, artifact_format="glb")
        self.assertEqual("models/gahyeon.glb", item["uri"])
        self.assertEqual(len(b"g1-model"), item["bytes"])
        payload = json.loads(self.g1.read_text())
        self.assertEqual(item, payload["modelArtifact"])
        self.assertEqual("draft", verify_g1(self.g1)["status"])

    def test_g1_refuses_role_and_second_model(self):
        before = self.g1.read_bytes()
        with self.assertRaisesRegex(ValueError, "does not accept"):
            record(self.g1, artifact_file=self.model, artifact_format="glb", role="model")
        self.assertEqual(before, self.g1.read_bytes())
        record(self.g1, artifact_file=self.model, artifact_format="glb")
        with self.assertRaisesRegex(ValueError, "already contains"):
            record(self.g1, artifact_file=self.model, artifact_format="glb")

    def test_g2_requires_unique_valid_role(self):
        g2 = self.root / "g2-review.json"
        create("G2", g2, previous=self.g1, allow_unapproved_predecessor=True)
        artifact = self.root / "models/high.blend"
        artifact.write_bytes(b"high-poly")
        with self.assertRaisesRegex(ValueError, "requires --role"):
            record(g2, artifact_file=artifact, artifact_format="blend")
        item = record(g2, artifact_file=artifact, artifact_format="blend",
                      role="high-poly-master")
        self.assertEqual("high-poly-master", item["role"])
        with self.assertRaisesRegex(ValueError, "already contains"):
            record(g2, artifact_file=artifact, artifact_format="blend",
                   role="high-poly-master")

    def test_invalid_format_fails_without_modifying_review(self):
        before = self.g1.read_bytes()
        with self.assertRaises(jsonschema.ValidationError):
            record(self.g1, artifact_file=self.model, artifact_format="exe")
        self.assertEqual(before, self.g1.read_bytes())

    def test_outside_symlink_and_final_review_are_rejected(self):
        outside = self.root.parent / "outside-quality-model.glb"
        outside.write_bytes(b"outside")
        link = self.root / "linked.glb"
        try:
            with self.assertRaisesRegex(ValueError, "inside the review workspace"):
                record(self.g1, artifact_file=outside, artifact_format="glb")
            link.symlink_to(self.model)
            with self.assertRaisesRegex(ValueError, "symbolic link"):
                record(self.g1, artifact_file=link, artifact_format="glb")
            payload = json.loads(self.g1.read_text())
            payload["status"] = "rejected"
            self.g1.write_text(json.dumps(payload))
            with self.assertRaisesRegex(ValueError, "cannot modify"):
                record(self.g1, artifact_file=self.model, artifact_format="glb")
        finally:
            outside.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
