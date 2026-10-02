import copy
import json
import tempfile
import unittest
from pathlib import Path

from character_pipeline.tools.worker_bootstrap import build_download_commands, validate_bootstrap_manifest


CONFIG = json.loads(Path("character_pipeline/config/worker_bootstrap.json").read_text())
SNAPSHOTS = json.loads(Path("character_pipeline/config/worker_handoff.json").read_text())


class WorkerBootstrapTest(unittest.TestCase):
    def test_contract_is_offline_and_pinned(self):
        result = validate_bootstrap_manifest(CONFIG, SNAPSHOTS)
        self.assertFalse(result["networkDefault"])
        self.assertGreaterEqual(result["snapshotFiles"], 7)

    def test_network_requires_explicit_opt_in(self):
        with tempfile.TemporaryDirectory() as install, tempfile.TemporaryDirectory() as cache:
            with self.assertRaisesRegex(ValueError, "explicit opt-in"):
                build_download_commands(CONFIG, SNAPSHOTS, Path(install), Path(cache),
                                        {"facebook-dinov3-license"}, False)

    def test_approval_required_and_forbidden_models_never_downloaded(self):
        with tempfile.TemporaryDirectory() as install, tempfile.TemporaryDirectory() as cache:
            with self.assertRaisesRegex(ValueError, "missing required approvals"):
                build_download_commands(CONFIG, SNAPSHOTS, Path(install), Path(cache), set(), True)
            commands = build_download_commands(CONFIG, SNAPSHOTS, Path(install), Path(cache),
                                                {"facebook-dinov3-license"}, True)
            flattened = " ".join(part for command in commands for part in command)
            self.assertNotIn("RMBG-2.0", flattened)
            self.assertNotIn("Hunyuan3D", flattened)
            self.assertIn("af44b45f2e35a493886929c6d786e563ec68364d", flattened)

    def test_relative_or_nonempty_install_root_rejected(self):
        with self.assertRaisesRegex(ValueError, "absolute"):
            build_download_commands(CONFIG, SNAPSHOTS, Path("install"), Path("cache"),
                                    {"facebook-dinov3-license"}, True)
        with tempfile.TemporaryDirectory() as install, tempfile.TemporaryDirectory() as cache:
            (Path(install) / "occupied").write_text("x")
            with self.assertRaisesRegex(ValueError, "must be empty"):
                build_download_commands(CONFIG, SNAPSHOTS, Path(install), Path(cache),
                                        {"facebook-dinov3-license"}, True)

    def test_removing_license_rejections_fails(self):
        config = copy.deepcopy(CONFIG)
        config["forbiddenModels"] = []
        with self.assertRaisesRegex(ValueError, "rejection"):
            validate_bootstrap_manifest(config, SNAPSHOTS)


if __name__ == "__main__":
    unittest.main()
