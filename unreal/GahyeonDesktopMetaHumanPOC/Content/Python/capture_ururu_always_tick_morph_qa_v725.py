"""Force offscreen skeletal refresh while testing v705 manual morph weights."""

from __future__ import annotations

from pathlib import Path


SOURCE = Path(__file__).with_name("capture_ururu_ue_settled_face_morph_qa_v701.py")
OLD_MESH = "/Game/LivingCharacterPOC/v693/Characters/UruruFacial/Ururu_StaticHeadMorphs_v691"
COMBINED_MESH = "/Game/LivingCharacterPOC/v705/Characters/UruruFacial/Ururu_HeadMorphs_Centimeter_v688"
OLD_SETUP = '        self.component.set_editor_property("skeletal_mesh_asset", mesh)'
TICK_SETUP = '''        self.component.set_editor_property("skeletal_mesh_asset", mesh)
        self.component.set_editor_property(
            "visibility_based_anim_tick_option",
            unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES,
        )
        self.component.set_component_tick_enabled(True)
        self.component.set_update_animation_in_editor(True)'''


def capture_ururu_always_tick_morph_qa_v725() -> None:
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    source = SOURCE.read_text(encoding="utf-8")
    if source.count("v701") < 10 or OLD_MESH not in source or OLD_SETUP not in source:
        raise RuntimeError("sealed v701 manual-morph protocol changed unexpectedly")
    source = source.replace(OLD_MESH, COMBINED_MESH)
    source = source.replace(OLD_SETUP, TICK_SETUP)
    source = source.replace("v701", "v725").replace("V701", "V725")
    exec(compile(source, str(SOURCE) + "::v725", "exec"), {"__name__": "__main__"})


capture_ururu_always_tick_morph_qa_v725()
