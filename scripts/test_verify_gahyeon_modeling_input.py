#!/usr/bin/env python3

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from verify_gahyeon_modeling_input import verify
from gahyeon_quality_test_fixture import write_source_pack


class ModelingInputVerificationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.source = Path(self.temp.name)
        identity_path, modeling_path = write_source_pack(self.source)
        self.identity = json.loads(identity_path.read_text(encoding="utf-8"))
        self.modeling = json.loads(modeling_path.read_text(encoding="utf-8"))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_pack(self, modeling: dict, identity: dict | None = None) -> Path:
        directory = self.source
        (directory / "identity-reference.json").write_text(
            json.dumps(identity or self.identity), encoding="utf-8")
        path = directory / "modeling-input.json"
        path.write_text(json.dumps(modeling), encoding="utf-8")
        return path

    def test_current_handoff_is_valid(self) -> None:
        references, anchors = verify(self.source / "modeling-input.json")
        self.assertEqual(18, references)
        self.assertGreaterEqual(anchors, 18)

    def test_unknown_anchor_is_rejected(self) -> None:
        candidate = copy.deepcopy(self.modeling)
        candidate["anchors"]["neutralFaceFront"] = [999]
        with self.assertRaisesRegex(ValueError, "unknown canonical index"):
            verify(self.write_pack(candidate))

    def test_full_body_cannot_define_face_geometry(self) -> None:
        candidate = copy.deepcopy(self.modeling)
        candidate["geometryAuthority"]["primaryFaceGeometry"] = [3, 16]
        with self.assertRaisesRegex(ValueError, "incompatible full-body"):
            verify(self.write_pack(candidate))

    def test_lora_cannot_be_promoted(self) -> None:
        identity = copy.deepcopy(self.identity)
        identity["auxiliaryModels"][0]["heroReferenceAllowed"] = True
        with self.assertRaisesRegex(ValueError, "LoRA output"):
            verify(self.write_pack(self.modeling, identity))


if __name__ == "__main__":
    unittest.main()
