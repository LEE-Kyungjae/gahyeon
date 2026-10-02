#!/usr/bin/env python3

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from create_gahyeon_quality_review import create
from gahyeon_quality_test_fixture import write_source_pack
from verify_gahyeon_g1_review import verify as verify_g1
from verify_gahyeon_g2_review import verify as verify_g2
from verify_gahyeon_g3_review import verify as verify_g3
from verify_gahyeon_g4_review import verify as verify_g4
from verify_gahyeon_g5_review import verify as verify_g5


class CreateQualityReviewTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.identity, self.modeling = write_source_pack(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_creates_checksum_bound_draft_chain(self):
        paths = {"G1": self.root / "G1.json"}
        create("G1", paths["G1"], identity=self.identity, modeling=self.modeling)
        previous = paths["G1"]
        for gate in ("G2", "G3", "G4", "G5"):
            paths[gate] = self.root / f"{gate}.json"
            create(gate, paths[gate], previous=previous,
                   allow_unapproved_predecessor=True)
            payload = json.loads(paths[gate].read_text())
            predecessor_field = f"g{int(gate[1]) - 1}Review"
            self.assertEqual(hashlib.sha256(previous.read_bytes()).hexdigest(),
                             payload[predecessor_field]["sha256"])
            previous = paths[gate]
        for path, verifier in zip(paths.values(),
                                  (verify_g1, verify_g2, verify_g3, verify_g4, verify_g5)):
            self.assertEqual("draft", verifier(path)["status"])

    def test_requires_approved_predecessor_by_default(self):
        g1 = self.root / "G1.json"
        create("G1", g1, identity=self.identity, modeling=self.modeling)
        with self.assertRaisesRegex(ValueError, "not approved"):
            create("G2", self.root / "G2.json", previous=g1)

    def test_refuses_overwrite(self):
        output = self.root / "G1.json"
        create("G1", output, identity=self.identity, modeling=self.modeling)
        before = output.read_bytes()
        with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
            create("G1", output, identity=self.identity, modeling=self.modeling)
        self.assertEqual(before, output.read_bytes())

    def test_refuses_cross_workspace_predecessor(self):
        g1 = self.root / "G1.json"
        create("G1", g1, identity=self.identity, modeling=self.modeling)
        other = self.root / "other"
        other.mkdir()
        with self.assertRaisesRegex(ValueError, "same review workspace"):
            create("G2", other / "G2.json", previous=g1,
                   allow_unapproved_predecessor=True)


if __name__ == "__main__":
    unittest.main()
