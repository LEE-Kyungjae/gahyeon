import unittest
from pathlib import Path


SCRIPT = Path("unreal/GahyeonStage/Content/Python/gahyeon_build_talking_full_body_v096.py")


class TalkingFullBodyV096ContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SCRIPT.read_text(encoding="utf-8")

    def test_preserves_verified_sequence(self):
        self.assertIn("v094/Sequence/LS_GahyeonTalkingControlRig_v094", self.source)
        self.assertIn("v096/Sequence", self.source)
        self.assertIn("refusing to overwrite v096 sequence", self.source)

    def test_resolves_camera_component_from_spawnable(self):
        self.assertIn("unreal.CineCameraComponent", self.source)
        self.assertIn("get_components_by_class", self.source)
        self.assertIn('"current_focal_length"', self.source)

    def test_remains_unapproved_until_render_review(self):
        self.assertIn('"runtimePlaybackVerified": False', self.source)
        self.assertIn('"humanApproved": False', self.source)
        self.assertIn('"productionReady": False', self.source)


if __name__ == "__main__":
    unittest.main()
