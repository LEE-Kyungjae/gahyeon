#!/usr/bin/env python3

import importlib.util
from pathlib import Path
import tempfile
import unittest

import numpy as np
from PIL import Image


SCRIPT = Path(__file__).with_name("compare_renders.py")
SPEC = importlib.util.spec_from_file_location("compare", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class CompareTest(unittest.TestCase):
    def test_reports_delta_without_quality_score(self):
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            a = np.zeros((2, 3, 4), dtype=np.uint8)
            a[:, :, 3] = 255
            b = a.copy()
            b[0, 1, 0] = 3
            Image.fromarray(a).save(root / "a.png")
            Image.fromarray(b).save(root / "b.png")
            result = MODULE.compare(root / "a.png", root / "b.png")
            self.assertFalse(result["identical"])
            self.assertEqual(result["pixelsAbove2"], 1)
            self.assertIsNone(result["qualityClaim"])


if __name__ == "__main__":
    unittest.main()
