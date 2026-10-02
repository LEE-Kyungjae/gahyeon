import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("run_keentools_postprocess_v175.py")
SPEC = importlib.util.spec_from_file_location("run_keentools_postprocess_v175", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class RunKeenToolsPostprocessV175Test(unittest.TestCase):
    def test_dry_run_has_three_non_overwriting_blender_stages(self):
        payload = MODULE.run_keentools_postprocess_v175(dry_run=True)
        self.assertTrue(payload["dryRun"])
        self.assertEqual(len(payload["commands"]), 3)
        flattened = [value for command in payload["commands"] for value in command]
        self.assertIn("--merge-distance-cm", flattened)
        self.assertIn("0.0", flattened)
        self.assertIn("1440", flattened)
        self.assertIn("2560", flattened)
        for view in MODULE.VIEWS:
            self.assertIn(view, flattened)

    def test_live_run_fails_before_mutation_without_download(self):
        if MODULE.MODEL.exists():
            self.skipTest("real v175 model is present")
        with self.assertRaisesRegex(RuntimeError, "GLB is missing"):
            MODULE.run_keentools_postprocess_v175(dry_run=False)


if __name__ == "__main__":
    unittest.main()
