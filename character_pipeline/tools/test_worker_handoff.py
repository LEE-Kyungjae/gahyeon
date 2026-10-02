import copy
import json
import unittest
from pathlib import Path

from character_pipeline.tools.worker_handoff import build_worker_handoff, validate_worker_handoff


CONFIG = json.loads(Path("character_pipeline/config/worker_handoff.json").read_text())
CAPABLE = {"os": "linux", "architecture": "x86_64", "nvidiaCuda": True,
           "gpu": "NVIDIA H100", "vramGiB": 80, "freeDiskGiB": 100}


class WorkerHandoffTest(unittest.TestCase):
    def test_current_contract_blocks_missing_gated_license_approval(self):
        handoff = build_worker_handoff(CONFIG, CAPABLE)
        result = validate_worker_handoff(CONFIG, handoff)
        self.assertEqual(result["state"], "blocked")
        self.assertEqual(handoff["models"]["trellis"]["blockers"], ["gated-license-approval-missing"])
        self.assertTrue(handoff["models"]["instantmesh"]["ready"])

    def test_insufficient_worker_is_blocked(self):
        handoff = build_worker_handoff(CONFIG, {**CAPABLE, "freeDiskGiB": 20})
        with self.assertRaisesRegex(ValueError, "free disk"):
            validate_worker_handoff(CONFIG, handoff)

    def test_checksum_tampering_fails(self):
        handoff = build_worker_handoff(CONFIG, CAPABLE)
        handoff["models"]["instantmesh"]["files"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "checksum"):
            validate_worker_handoff(CONFIG, handoff)

    def test_extra_file_fails_allowlist(self):
        handoff = build_worker_handoff(CONFIG, CAPABLE)
        handoff["models"]["instantmesh"]["files"].append({"path": "other.bin", "bytes": 1, "sha256": "0" * 64})
        with self.assertRaisesRegex(ValueError, "inventory"):
            validate_worker_handoff(CONFIG, handoff)

    def test_overclaimed_ready_fails(self):
        handoff = build_worker_handoff(CONFIG, CAPABLE)
        handoff["state"] = "ready"
        with self.assertRaisesRegex(ValueError, "overclaims"):
            validate_worker_handoff(CONFIG, handoff)

    def test_explicit_gated_license_approval_allows_ready_fixture(self):
        handoff = build_worker_handoff(CONFIG, CAPABLE, {
            "facebook/dinov3-vitl16-pretrain-lvd1689m": {
                "acceptedBy": "fixture-reviewer", "acceptedAt": "2026-08-13T00:00:00Z"
            }
        })
        self.assertEqual(validate_worker_handoff(CONFIG, handoff)["state"], "ready")


if __name__ == "__main__":
    unittest.main()
