#!/usr/bin/env python3

import json
from pathlib import Path
import subprocess
import tempfile
import unittest


TOOLS = Path(__file__).resolve().parent


class IterationContractTest(unittest.TestCase):
    def test_create_is_monotonic_and_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            command = ["python3", str(TOOLS / "create_iteration.py"), "--root", str(root),
                       "--hypothesis", "shape is too wide", "--action", "measure width",
                       "--expected", "measurement becomes available"]
            first = Path(subprocess.check_output(command, text=True).strip())
            second = Path(subprocess.check_output(command, text=True).strip())
            self.assertEqual(first.parent.name, "v001")
            self.assertEqual(second.parent.name, "v002")
            self.assertTrue((first.parent / "generation/trellis").is_dir())
            self.assertTrue((first.parent / "generation/instantmesh").is_dir())

    def test_overall_cannot_hide_missing_components(self):
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            manifest = Path(subprocess.check_output([
                "python3", str(TOOLS / "create_iteration.py"), "--root", str(root),
                "--hypothesis", "x", "--action", "y", "--expected", "z"], text=True).strip())
            data = json.loads(manifest.read_text())
            data["evaluation"]["scores"]["overall"] = 90
            manifest.write_text(json.dumps(data))
            result = subprocess.run([
                "python3", str(TOOLS / "verify_iteration.py"), str(manifest.parent)
            ], text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("overall score requires", result.stderr)


if __name__ == "__main__":
    unittest.main()
