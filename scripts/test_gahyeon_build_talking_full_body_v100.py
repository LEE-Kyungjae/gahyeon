import unittest
from pathlib import Path


class TalkingFullBodyV100ContractTest(unittest.TestCase):
    def test_measured_camera_contract(self):
        source = Path(
            "unreal/GahyeonStage/Content/Python/gahyeon_build_talking_full_body_v100.py"
        ).read_text(encoding="utf-8")
        self.assertIn("v100/Sequence", source)
        self.assertIn("FOCAL_LENGTH_MM = 3.5", source)
        self.assertIn("CAMERA_HEIGHT_CM = 125.0", source)
        self.assertIn("refusing to overwrite v100 sequence", source)


if __name__ == "__main__":
    unittest.main()
