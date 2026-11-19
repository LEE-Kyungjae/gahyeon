"""Test manual morph weights on the v692 Interchange mesh and its own skeleton."""

from __future__ import annotations

from pathlib import Path


SOURCE = Path(__file__).with_name("capture_ururu_ue_settled_face_morph_qa_v701.py")
OLD_MESH = "/Game/LivingCharacterPOC/v693/Characters/UruruFacial/Ururu_StaticHeadMorphs_v691"
OLD_SKELETON = "/Game/LivingCharacterPOC/v585/Characters/UruruCentimeterNormalized/Ururu_CentimeterNormalized_v584_Skeleton"
INTERCHANGE_ROOT = "/Game/LivingCharacterPOC/v692/Characters/UruruFacial/Ururu_StaticHeadMorphs_v691"


def capture_ururu_interchange_morph_qa_v722() -> None:
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    source = SOURCE.read_text(encoding="utf-8")
    if source.count("v701") < 10 or OLD_MESH not in source or OLD_SKELETON not in source:
        raise RuntimeError("sealed v701 manual-morph protocol changed unexpectedly")
    source = source.replace(OLD_MESH, INTERCHANGE_ROOT)
    source = source.replace(OLD_SKELETON, INTERCHANGE_ROOT + "_Skeleton")
    source = source.replace("v701", "v722").replace("V701", "V722")
    exec(compile(source, str(SOURCE) + "::v722", "exec"), {"__name__": "__main__"})


capture_ururu_interchange_morph_qa_v722()
