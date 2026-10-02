#!/usr/bin/env python3

import json
from pathlib import Path
import tempfile
import unittest

from character_pipeline.tools.photogrammetric_head_contract import (
    build_photogrammetric_head_job,
    validate_photogrammetric_head_job,
)


ROOT = Path(__file__).resolve().parents[2]


class PhotogrammetricHeadContractTest(unittest.TestCase):
    def test_real_identity_builds_fail_closed_multiview_job(self):
        config = json.loads((ROOT / "character_pipeline/config/photogrammetric_head.json").read_text())
        job = build_photogrammetric_head_job(
            config, ROOT / "artifacts/gahyeon-ch/identity-reference.json")
        result = validate_photogrammetric_head_job(job)
        self.assertTrue(result["valid"])
        self.assertEqual(result["references"], 4)
        self.assertFalse(job["productionMeshAllowed"])
        self.assertEqual(job["target"]["operation"], "MetaHuman From Custom Mesh")

    def test_changed_reference_is_rejected(self):
        config = json.loads((ROOT / "character_pipeline/config/photogrammetric_head.json").read_text())
        job = build_photogrammetric_head_job(
            config, ROOT / "artifacts/gahyeon-ch/identity-reference.json")
        with tempfile.TemporaryDirectory() as value:
            changed = Path(value) / "changed.png"
            changed.write_bytes(b"not the canonical image")
            job["references"][0]["path"] = str(changed.resolve())
            with self.assertRaisesRegex(ValueError, "reference lineage differs"):
                validate_photogrammetric_head_job(job)

    def test_metahuman_target_cannot_be_downgraded(self):
        config = json.loads((ROOT / "character_pipeline/config/photogrammetric_head.json").read_text())
        job = build_photogrammetric_head_job(
            config, ROOT / "artifacts/gahyeon-ch/identity-reference.json")
        job["target"]["finalTopology"] = "reconstruction-mesh"
        with self.assertRaisesRegex(ValueError, "target contract differs"):
            validate_photogrammetric_head_job(job)


if __name__ == "__main__":
    unittest.main()
