import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "unreal/GahyeonStage/Content/Python/gahyeon_build_talking_poc_v092.py"
PROJECT = ROOT / "unreal/GahyeonStage/GahyeonStageTalkingPOC.uproject"


class TalkingPocV092ContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SCRIPT.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_targets_retained_v088_without_modifying_it(self):
        self.assertIn("CharacterPipeline/v088", self.source)
        self.assertIn('ASSET_ROOT = "/Game/Gahyeon/TalkingPOC/v092"', self.source)
        self.assertNotIn("save_asset(BLUEPRINT", self.source)

    def test_uses_official_audio_driven_full_face_export(self):
        self.assertIn('process_mask="FullFace"', self.source)
        self.assertIn("export_animation_sequence", self.source)
        self.assertIn("v088/CommonMedium/Face/Face_Archetype_Skeleton", self.source)
        self.assertIn('head_movement_mode="ControlRig"', self.source)

    def test_refuses_overwrite_and_never_claims_visual_acceptance(self):
        self.assertGreaterEqual(self.source.count("refusing to overwrite"), 1)
        self.assertIn('"visualPlaybackVerified": False', self.source)
        self.assertIn('"productionReady": False', self.source)

    def test_talking_project_enables_mha_without_missing_websockets(self):
        project = PROJECT.read_text(encoding="utf-8")
        self.assertIn('{"Name": "MetaHuman", "Enabled": true}', project)
        self.assertIn('"MetaHumanCharacter"', project)
        self.assertNotIn('"WebSockets"', project)


if __name__ == "__main__":
    unittest.main()
