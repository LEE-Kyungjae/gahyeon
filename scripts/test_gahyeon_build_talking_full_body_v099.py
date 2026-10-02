import unittest
from pathlib import Path


class TalkingFullBodyV099ContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path(
            "unreal/GahyeonStage/Content/Python/gahyeon_build_talking_full_body_v099.py"
        ).read_text(encoding="utf-8")

    def test_is_new_head_to_toe_iteration(self):
        self.assertIn("v094/Sequence/LS_GahyeonTalkingControlRig_v094", self.source)
        self.assertIn("v099/Sequence", self.source)
        self.assertIn("FOCAL_LENGTH_MM = 5.0", self.source)
        self.assertIn("CAMERA_HEIGHT_CM = 95.0", self.source)

    def test_changes_only_camera_focal_and_height_channels(self):
        self.assertIn('display == "CurrentFocalLength"', self.source)
        self.assertIn('startswith("Location.Z")', self.source)
        self.assertIn('sorted(changed) != ["focal", "height"]', self.source)


if __name__ == "__main__":
    unittest.main()
