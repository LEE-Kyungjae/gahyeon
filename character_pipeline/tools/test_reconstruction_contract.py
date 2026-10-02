#!/usr/bin/env python3

import json
from pathlib import Path
import subprocess
import tempfile
import unittest


TOOLS = Path(__file__).resolve().parent


class ReconstructionContractTest(unittest.TestCase):
    def test_models_are_separate_and_monotonic(self):
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            source = root / "input.json"
            source.write_text("{}")
            def create(model):
                return Path(subprocess.check_output([
                    "python3", str(TOOLS / "create_reconstruction_candidate.py"),
                    "--root", str(root), "--model", model, "--iteration", "v001",
                    "--input-manifest", str(source), "--seed", "42"], text=True).strip())
            self.assertEqual(create("trellis").parent.name, "candidate_001")
            self.assertEqual(create("trellis").parent.name, "candidate_002")
            self.assertEqual(create("instantmesh").parent.name, "candidate_001")

    def test_generated_candidate_requires_pinned_provenance(self):
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            source = root / "input.json"
            source.write_text("{}")
            manifest = Path(subprocess.check_output([
                "python3", str(TOOLS / "create_reconstruction_candidate.py"),
                "--root", str(root), "--model", "trellis", "--iteration", "v001",
                "--input-manifest", str(source), "--seed", "1"], text=True).strip())
            data = json.loads(manifest.read_text())
            data["status"] = "generated"
            manifest.write_text(json.dumps(data))
            result = subprocess.run(["python3", str(TOOLS / "verify_reconstruction_candidate.py"),
                                     str(manifest.parent)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("requires provenance", result.stderr)


if __name__ == "__main__":
    unittest.main()
