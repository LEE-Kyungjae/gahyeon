"""Use the QA bridge to refresh v705 manual morphs before fixed-camera capture."""

from __future__ import annotations

from pathlib import Path


SOURCE = Path(__file__).with_name("capture_ururu_ue_settled_face_morph_qa_v701.py")
OLD_MESH = "/Game/LivingCharacterPOC/v693/Characters/UruruFacial/Ururu_StaticHeadMorphs_v691"
COMBINED_MESH = "/Game/LivingCharacterPOC/v705/Characters/UruruFacial/Ururu_HeadMorphs_Centimeter_v688"
OLD_APPLY = '''        for name, value in values.items():
            self.component.set_morph_target(name, value, False)
'''
REFRESHED_APPLY = '''        for name, value in values.items():
            self.component.set_morph_target(name, value, False)
        success, message = unreal.GahyeonMetaHumanQALibrary.force_refresh_skeletal_morphs(
            self.component,
        )
        if not success:
            raise RuntimeError(f"v727 skeletal morph refresh failed: {message}")
'''


def capture_ururu_forced_refresh_morph_qa_v727() -> None:
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    source = SOURCE.read_text(encoding="utf-8")
    if source.count("v701") < 10 or OLD_MESH not in source or OLD_APPLY not in source:
        raise RuntimeError("sealed v701 manual-morph protocol changed unexpectedly")
    source = source.replace(OLD_MESH, COMBINED_MESH)
    source = source.replace(OLD_APPLY, REFRESHED_APPLY)
    source = source.replace("v701", "v727").replace("V701", "V727")
    exec(compile(source, str(SOURCE) + "::v727", "exec"), {"__name__": "__main__"})


capture_ururu_forced_refresh_morph_qa_v727()
