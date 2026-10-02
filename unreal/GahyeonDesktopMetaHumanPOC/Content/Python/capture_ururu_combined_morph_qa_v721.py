"""Test manual morph weights on the v705 combined mesh import."""

from __future__ import annotations

from pathlib import Path


SOURCE = Path(__file__).with_name("capture_ururu_ue_settled_face_morph_qa_v701.py")
OLD_MESH = "/Game/LivingCharacterPOC/v693/Characters/UruruFacial/Ururu_StaticHeadMorphs_v691"
COMBINED_MESH = "/Game/LivingCharacterPOC/v705/Characters/UruruFacial/Ururu_HeadMorphs_Centimeter_v688"


def capture_ururu_combined_morph_qa_v721() -> None:
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    source = SOURCE.read_text(encoding="utf-8")
    if source.count("v701") < 10 or OLD_MESH not in source:
        raise RuntimeError("sealed v701 manual-morph protocol changed unexpectedly")
    source = source.replace(OLD_MESH, COMBINED_MESH)
    source = source.replace("v701", "v721").replace("V701", "V721")
    exec(compile(source, str(SOURCE) + "::v721", "exec"), {"__name__": "__main__"})


capture_ururu_combined_morph_qa_v721()
