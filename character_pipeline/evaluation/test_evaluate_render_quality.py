import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from character_pipeline.evaluation.evaluate_render_quality import evaluate


class RenderQualityTest(unittest.TestCase):
    def test_valid_face_capture(self):
        pixels = np.full((256, 144, 3), 90, dtype=np.uint8)
        pixels[20:235, 30:115] = 150
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "face.png"
            Image.fromarray(pixels).save(path)
            result = evaluate(path, (144, 256), face_view=True)
        self.assertTrue(result["validCapture"])

    def test_dark_clipped_capture_fails(self):
        pixels = np.full((256, 144, 3), 90, dtype=np.uint8)
        pixels[:, 10:140] = 20
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "face.png"
            Image.fromarray(pixels).save(path)
            result = evaluate(path, (144, 256), face_view=True)
        self.assertFalse(result["validCapture"])
        self.assertIn("subject-clipped-or-too-close-to-frame", result["defects"])
        self.assertIn("foreground-too-dark", result["defects"])


if __name__ == "__main__":
    unittest.main()
