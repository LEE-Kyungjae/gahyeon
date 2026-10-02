import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from verify_gahyeon_official_groom_route import verify


class OfficialGroomRouteTest(unittest.TestCase):
    def test_v087_uses_pipeline_without_transform_hacks(self):
        verify(
            Path(__file__).parents[1]
            / "unreal/GahyeonStage/Content/Python/gahyeon_build_official_wardrobe_groom_v087.py"
        )

    def test_direct_component_mutation_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "bad.py"
            candidate.write_text(
                "try_add_item_from_wardrobe_item MetaHumanPipelineSlotSelection "
                "try_add_slot_selection MetaHumanCharacterEditorSubsystem "
                "assemble_for_preview set_relative_location("
            )
            with self.assertRaises(ValueError):
                verify(candidate)


if __name__ == "__main__":
    unittest.main()
