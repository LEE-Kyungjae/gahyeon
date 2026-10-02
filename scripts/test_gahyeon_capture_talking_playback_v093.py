import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "unreal/GahyeonStage/Content/Python/gahyeon_capture_talking_playback_v093.py"
PROJECT = ROOT / "unreal/GahyeonStage/GahyeonStageTalkingPlayback.uproject"


class TalkingPlaybackCaptureV093Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SCRIPT.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_uses_retained_character_and_generated_animation(self):
        self.assertIn("WardrobeGroomQA_v088", self.source)
        self.assertIn("AS_GahyeonTalkingFace_v092", self.source)

    def test_captures_multiple_fixed_times_without_source_save(self):
        self.assertIn("SAMPLE_TIMES = (0.0, 1.5, 3.0, 5.0)", self.source)
        self.assertIn("take_high_res_screenshot", self.source)
        self.assertNotIn("save_loaded_asset", self.source)
        self.assertNotIn("save_map", self.source)

    def test_marks_capture_pending_before_reentrant_screenshot_call(self):
        pending = self.source.index("self.pending = (sample_time, path, time.monotonic())")
        screenshot = self.source.index(
            "unreal.AutomationLibrary.take_high_res_screenshot(1600, 1600, str(path), self.camera)")
        self.assertLess(pending, screenshot)

    def test_ticks_animation_before_freezing_each_sample(self):
        play = self.source.index("self.face.play(False)")
        position = self.source.index("self.face.set_position(sample_time, False)")
        advance = self.source.index("self.face.set_play_rate(1.0)")
        self.assertLess(play, position)
        self.assertLess(position, advance)
        self.assertIn("self.settling = (sample_time, time.monotonic() + 0.25)", self.source)
        self.assertGreaterEqual(self.source.count("self.face.set_play_rate(0.0)"), 2)

    def test_never_auto_approves(self):
        self.assertIn('"humanApproved": False', self.source)
        self.assertIn('"automaticApproval": False', self.source)

    def test_windows_playback_project_is_content_only(self):
        project = PROJECT.read_text(encoding="utf-8")
        self.assertNotIn('"Modules"', project)
        self.assertIn('{"Name": "MetaHuman", "Enabled": true}', project)


if __name__ == "__main__":
    unittest.main()
