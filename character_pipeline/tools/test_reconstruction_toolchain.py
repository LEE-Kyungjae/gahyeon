import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from character_pipeline.tools.reconstruction_toolchain import (
    build_generation_command, validate_toolchain_preflight,
)


CONFIG = json.loads(Path("character_pipeline/config/reconstruction_toolchains.json").read_text())


class ReconstructionToolchainTest(unittest.TestCase):
    def test_current_mac_is_truthfully_blocked(self):
        report = validate_toolchain_preflight(CONFIG, {
            "os": "darwin", "architecture": "arm64", "nvidiaCuda": False, "maximumVramGiB": 0,
        })
        self.assertEqual(report["state"], "blocked")
        self.assertIn("weights-checksum-missing", report["models"]["instantmesh"]["blockers"])
        self.assertIn("weights-checksum-missing", report["models"]["trellis"]["blockers"])

    def test_instantmesh_ready_on_capable_pinned_cuda_host(self):
        config = copy.deepcopy(CONFIG)
        config["models"]["instantmesh"]["weightsSha256"] = "a" * 64
        report = validate_toolchain_preflight(config, {
            "os": "linux", "architecture": "x86_64", "nvidiaCuda": True, "maximumVramGiB": 80,
        })
        self.assertTrue(report["models"]["instantmesh"]["ready"])

    def test_hunyuan_rejection_cannot_be_removed(self):
        config = copy.deepcopy(CONFIG)
        config.pop("historicalRejectedBackend")
        with self.assertRaisesRegex(ValueError, "territory rejection"):
            validate_toolchain_preflight(config, {
                "os": "linux", "architecture": "x86_64", "nvidiaCuda": True, "maximumVramGiB": 80,
            })

    def test_trellis_ready_only_with_reviewed_license_and_pinned_weights(self):
        config = copy.deepcopy(CONFIG)
        config["models"]["trellis"]["licenseReviewed"] = True
        config["models"]["trellis"]["weightsSha256"] = "b" * 64
        report = validate_toolchain_preflight(config, {
            "os": "linux", "architecture": "x86_64", "nvidiaCuda": True, "maximumVramGiB": 24,
        })
        self.assertTrue(report["models"]["trellis"]["ready"])

    @patch("character_pipeline.tools.reconstruction_toolchain.local_capabilities")
    def test_command_is_argv_and_contains_pins(self, capabilities):
        capabilities.return_value = {
            "os": "linux", "architecture": "x86_64", "nvidiaCuda": True, "maximumVramGiB": 80,
        }
        config = copy.deepcopy(CONFIG)
        config["models"]["trellis"]["licenseReviewed"] = True
        config["models"]["trellis"]["weightsSha256"] = "c" * 64
        command = build_generation_command(config, "trellis", Path("/work/candidate"),
                                           Path("/work/input.png"), 20260813)
        self.assertIsInstance(command, list)
        self.assertIn(config["models"]["trellis"]["revision"], command)
        self.assertIn("c" * 64, command)

    def test_relative_paths_are_rejected(self):
        with self.assertRaises(ValueError):
            build_generation_command(CONFIG, "trellis", Path("candidate"), Path("input.png"), 1)


if __name__ == "__main__":
    unittest.main()
