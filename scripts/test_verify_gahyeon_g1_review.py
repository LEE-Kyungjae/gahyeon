#!/usr/bin/env python3

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import jsonschema

from verify_gahyeon_g1_review import REQUIRED_VIEWS, verify
from gahyeon_quality_test_fixture import write_source_pack


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class G1ReviewTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        write_source_pack(self.root)
        self.payload = {
            "schemaVersion": 1, "characterId": "gahyeon", "gate": "G1", "status": "draft",
            "sourceManifests": [
                {"kind": "identity-reference", "uri": "identity-reference.json",
                 "sha256": sha(self.root / "identity-reference.json")},
                {"kind": "modeling-input", "uri": "modeling-input.json",
                 "sha256": sha(self.root / "modeling-input.json")},
            ],
            "evidence": [],
            "artistAuthoredRegions": ["rear-body", "rear-hair", "top-hair", "rear-outfit"],
            "findings": [], "approvals": [],
        }
        self.manifest = self.root / "review.json"

    def tearDown(self):
        self.temp.cleanup()

    def write(self, payload=None):
        self.manifest.write_text(json.dumps(payload or self.payload), encoding="utf-8")

    def approved(self):
        payload = copy.deepcopy(self.payload)
        payload["status"] = "approved"
        for index, view in enumerate(sorted(REQUIRED_VIEWS)):
            path = self.root / f"evidence-{index}.png"
            path.write_bytes(f"evidence:{view}".encode())
            authority = "artist-authored-completion" if view in {
                "body-neutral-rear", "hair-rear", "hair-top", "outfit-rear"} else "canonical-observed"
            payload["evidence"].append({"view": view, "captureType": "viewport-render",
                                        "designAuthority": authority, "uri": path.name,
                                        "sha256": sha(path)})
        model = self.root / "gahyeon-g1.glb"
        model.write_bytes(b"model")
        payload["modelArtifact"] = {"format": "glb", "uri": model.name,
                                    "sha256": sha(model), "bytes": model.stat().st_size}
        payload["approvals"] = [
            {"role": role, "reviewer": role, "approvedAt": "2026-08-12T12:00:00+09:00"}
            for role in ("identity-reviewer", "technical-reviewer", "operator")]
        return payload

    def test_draft_is_valid_but_not_approved(self):
        self.write()
        result = verify(self.manifest)
        self.assertEqual(15, len(result["missingRequiredViews"]))
        with self.assertRaisesRegex(ValueError, "not approved"):
            verify(self.manifest, require_approved=True)

    def test_complete_approved_review_passes(self):
        self.write(self.approved())
        result = verify(self.manifest, require_approved=True)
        self.assertEqual([], result["missingRequiredViews"])

    def test_missing_view_fails_approved(self):
        payload = self.approved()
        payload["evidence"].pop()
        self.write(payload)
        with self.assertRaises((ValueError, jsonschema.ValidationError)):
            verify(self.manifest, require_approved=True)

    def test_checksum_mismatch_fails(self):
        payload = self.approved()
        payload["evidence"][0]["sha256"] = "0" * 64
        self.write(payload)
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            verify(self.manifest)

    def test_path_escape_fails(self):
        payload = copy.deepcopy(self.payload)
        payload["sourceManifests"][0]["uri"] = "../identity-reference.json"
        self.write(payload)
        with self.assertRaisesRegex(ValueError, "escapes"):
            verify(self.manifest)

    def test_hidden_rear_cannot_claim_canonical_authority(self):
        payload = self.approved()
        rear = next(item for item in payload["evidence"] if item["view"] == "hair-rear")
        rear["designAuthority"] = "canonical-observed"
        self.write(payload)
        with self.assertRaisesRegex(ValueError, "cannot claim canonical"):
            verify(self.manifest)

    def test_symlink_escape_fails(self):
        outside = self.root.parent / "outside-g1-evidence.png"
        outside.write_bytes(b"outside")
        link = self.root / "linked-evidence.png"
        try:
            link.symlink_to(outside)
            payload = self.approved()
            payload["evidence"][0]["uri"] = link.name
            payload["evidence"][0]["sha256"] = sha(outside)
            self.write(payload)
            with self.assertRaisesRegex(ValueError, "resolves outside"):
                verify(self.manifest)
        finally:
            outside.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
