#!/usr/bin/env python3
"""Tests for donor outfit acceptance gates."""

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("verify_gahyeon_donor_outfit_candidate.py")
SPEC = importlib.util.spec_from_file_location("donor_gate", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def candidate(vertices=4000):
    piece = {
        "vertices": vertices,
        "vertexGroups": 12,
        "materials": ["PBR"],
    }
    return {
        "state": "extracted-donor-candidate",
        "identityAuthority": False,
        "productionReady": False,
        "source": {"file": "/licensed/source.blend", "sha256": "a" * 64},
        "objects": {
            "top": dict(piece),
            "bottom": dict(piece),
            "rig": {"deformBones": 100},
        },
    }


class DonorGateTest(unittest.TestCase):
    def test_good_geometry_can_advance_to_static_conform(self):
        result = MODULE.verify(candidate())
        self.assertTrue(result["readyForStaticConform"])
        self.assertFalse(result["readyForWeightTransfer"])

    def test_low_resolution_is_rejected(self):
        result = MODULE.verify(candidate(vertices=500))
        self.assertFalse(result["readyForStaticConform"])
        self.assertTrue(any("minimum" in defect for defect in result["defects"]))

    def test_render_retention_is_required_for_weight_transfer(self):
        retained = {"pipelinePocSucceeded": True, "retainForWeightTransfer": True}
        rejected = {"pipelinePocSucceeded": True, "retainForWeightTransfer": False}
        self.assertTrue(MODULE.verify(candidate(), retained)["readyForWeightTransfer"])
        self.assertFalse(MODULE.verify(candidate(), rejected)["readyForWeightTransfer"])


if __name__ == "__main__":
    unittest.main()
