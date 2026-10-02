import unittest
from pathlib import Path


SCRIPT = Path("unreal/GahyeonStage/Content/Python/gahyeon_build_talking_full_body_v097.py")


class TalkingFullBodyV097ContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SCRIPT.read_text(encoding="utf-8")

    def test_uses_new_iteration(self):
        self.assertIn("v094/Sequence/LS_GahyeonTalkingControlRig_v094", self.source)
        self.assertIn("v097/Sequence", self.source)
        self.assertIn("refusing to overwrite v097 sequence", self.source)

    def test_changes_focal_length_track(self):
        self.assertIn('binding.get_name() != "CameraComponent"', self.source)
        self.assertIn('track.get_display_name()) != "CurrentFocalLength"', self.source)
        self.assertIn("channel.set_default(FOCAL_LENGTH_MM)", self.source)
        self.assertIn("key.set_value(FOCAL_LENGTH_MM)", self.source)

    def test_is_not_approved_without_render(self):
        self.assertIn('"runtimePlaybackVerified": False', self.source)
        self.assertIn('"humanApproved": False', self.source)


if __name__ == "__main__":
    unittest.main()
