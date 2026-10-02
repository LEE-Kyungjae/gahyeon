import unittest
from pathlib import Path


class TalkingFullBodyV098ContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path(
            "unreal/GahyeonStage/Content/Python/gahyeon_build_talking_full_body_v098.py"
        ).read_text(encoding="utf-8")

    def test_is_isolated_and_wider_than_rejected_v097(self):
        self.assertIn("v094/Sequence/LS_GahyeonTalkingControlRig_v094", self.source)
        self.assertIn("v098/Sequence", self.source)
        self.assertIn("FOCAL_LENGTH_MM = 5.0", self.source)

    def test_refuses_overwrite_and_changes_only_focal_channel(self):
        self.assertIn("refusing to overwrite v098 sequence", self.source)
        self.assertIn('binding.get_name() != "CameraComponent"', self.source)
        self.assertIn('track.get_display_name()) != "CurrentFocalLength"', self.source)


if __name__ == "__main__":
    unittest.main()
