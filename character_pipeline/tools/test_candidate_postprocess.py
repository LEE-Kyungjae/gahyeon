import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from character_pipeline.tools.candidate_postprocess import (
    GO_VIEWS, build_postprocess_plan, digest, execute_postprocess,
    validate_candidate_receipt, validate_postprocess_state, write_json_atomic,
)

CONFIG = json.loads(Path("character_pipeline/config/candidate_postprocess.json").read_text())


class CandidatePostprocessTest(unittest.TestCase):
    def fixture(self, root):
        candidate = root / "generation/trellis/candidate_001"
        (candidate / "raw").mkdir(parents=True)
        mesh = candidate / "raw/mesh.glb"
        mesh.write_bytes(b"glTF" + b"x" * 2048)
        receipt = {"model": "trellis", "seed": 20260813,
                   "claim": "temporary-shape-estimate-not-production-mesh", "productionMeshAllowed": False,
                   "mesh": {"file": "mesh.glb", "bytes": mesh.stat().st_size, "sha256": digest(mesh)}}
        (candidate / "raw/result.json").write_text(json.dumps(receipt))
        (candidate / "candidate.json").write_text(json.dumps({"status": "generated", "outputs": [
            {"role": "raw-mesh", "sha256": digest(mesh)},
            {"role": "runner-receipt", "sha256": digest(candidate / "raw/result.json")},
        ]}))
        return candidate

    def plan(self, root):
        candidate = self.fixture(root)
        return candidate, build_postprocess_plan(CONFIG, candidate, Path("/usr/bin/blender"), Path.cwd())

    def test_plan_has_exact_go_contract_and_safe_argv(self):
        with tempfile.TemporaryDirectory() as directory:
            _, plan = self.plan(Path(directory))
            result = validate_postprocess_state(CONFIG, plan)
            self.assertEqual((result["views"], result["stages"]), (9, 16))
            self.assertEqual(plan["panelResolution"], [1440, 2560])
            self.assertEqual(plan["views"], GO_VIEWS)
            self.assertTrue(all(isinstance(item["argv"], list) for item in plan["commands"]))

    def test_receipt_or_mesh_tamper_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            candidate = self.fixture(Path(directory))
            (candidate / "raw/mesh.glb").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "differs"):
                validate_candidate_receipt(candidate)

    def test_existing_output_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            candidate = self.fixture(Path(directory))
            (candidate / "postprocess").mkdir()
            (candidate / "postprocess/x").write_text("x")
            with self.assertRaisesRegex(ValueError, "already exists"):
                build_postprocess_plan(CONFIG, candidate, Path("/b"), Path.cwd())

    def test_view_or_state_overclaim_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            _, plan = self.plan(Path(directory))
            plan["expected"]["views"].pop()
            with self.assertRaisesRegex(ValueError, "views differ"):
                validate_postprocess_state(CONFIG, plan)

    def test_failure_records_stage_and_resume_verifies_prefix(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, plan = self.plan(root)
            state_path = root / "state.json"
            write_json_atomic(state_path, plan)
            calls = []

            def fake_runner(argv, check):
                command = plan["commands"][len(calls)]
                calls.append(command["id"])
                if command["id"] == "render":
                    raise subprocess.CalledProcessError(2, argv)
                for output in command["outputs"]:
                    path = Path(output); path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b"valid")

            with self.assertRaises(subprocess.CalledProcessError):
                execute_postprocess(CONFIG, state_path, fake_runner)
            failed = json.loads(state_path.read_text())
            self.assertEqual((failed["state"], failed["failure"]["stage"]), ("failed", "render"))
            self.assertEqual(len(failed["completed"]), 2)

            def success_runner(argv, check):
                command = plan["commands"][len(json.loads(state_path.read_text())["completed"])]
                for output in command["outputs"]:
                    path = Path(output); path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b"valid")

            completed = execute_postprocess(CONFIG, state_path, success_runner)
            self.assertEqual((completed["state"], len(completed["completed"])), ("completed", 16))
            Path(completed["commands"][0]["outputs"][0]).write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "checksum differs"):
                execute_postprocess(CONFIG, state_path, success_runner)


if __name__ == "__main__":
    unittest.main()
