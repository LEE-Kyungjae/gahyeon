import ast
import unittest
from pathlib import Path


SCRIPT = Path("unreal/GahyeonStage/Content/Python/gahyeon_build_talking_full_body_v095.py")


class TalkingFullBodyV095ContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SCRIPT.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_uses_new_iteration_and_preserves_source(self):
        self.assertIn("v094/Sequence/LS_GahyeonTalkingControlRig_v094", self.source)
        self.assertIn("v095/Sequence", self.source)
        self.assertIn("refusing to overwrite v095 sequence", self.source)

    def test_changes_only_the_sequence_camera_template(self):
        self.assertIn("duplicate_asset", self.source)
        self.assertIn("isinstance(template, unreal.CineCameraActor)", self.source)
        self.assertIn('"current_focal_length"', self.source)
        self.assertNotIn("target_meta_human_class", self.source)

    def test_receipt_is_fail_closed(self):
        self.assertIn('"runtimePlaybackVerified": False', self.source)
        self.assertIn('"humanApproved": False', self.source)
        self.assertIn('"productionReady": False', self.source)


if __name__ == "__main__":
    unittest.main()
