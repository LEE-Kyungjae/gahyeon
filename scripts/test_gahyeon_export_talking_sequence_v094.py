import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "unreal/GahyeonStage/Content/Python/gahyeon_export_talking_sequence_v094.py"


class TalkingSequenceV094Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SCRIPT.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_targets_v088_and_processed_v092(self):
        self.assertIn("WardrobeGroomQA_v088", self.source)
        self.assertIn("GahyeonTalkingPerformance_v092", self.source)

    def test_uses_control_rig_without_invalid_audio_video_track(self):
        self.assertIn("settings.export_control_rig_track = True", self.source)
        self.assertIn("settings.export_video_track = False", self.source)
        self.assertIn("settings.export_audio_track = True", self.source)

    def test_is_new_fail_closed_iteration(self):
        self.assertIn("TalkingPOC/v094", self.source)
        self.assertIn("refusing to overwrite", self.source)
        self.assertIn('"runtimePlaybackVerified": False', self.source)


if __name__ == "__main__":
    unittest.main()
