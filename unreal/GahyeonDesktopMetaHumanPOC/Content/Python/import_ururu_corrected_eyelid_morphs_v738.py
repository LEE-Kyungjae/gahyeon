"""Import v737 corrected eyelids using the validated v705 FBX protocol."""

from __future__ import annotations

from pathlib import Path


SOURCE = Path(__file__).with_name("import_ururu_animated_head_morphs_v705.py")
OLD_FBX = "artifacts/living-character-poc-v688-ururu-centimeter-head-morphs/Ururu_HeadMorphs_Centimeter_v688.fbx"
NEW_FBX = "artifacts/living-character-poc-v737-ururu-corrected-eyelid-winding/Ururu_HeadMorphs_CorrectedEyelids_v737.fbx"


def import_ururu_corrected_eyelid_morphs_v738() -> None:
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    source = SOURCE.read_text(encoding="utf-8")
    if source.count("v705") < 8 or OLD_FBX not in source:
        raise RuntimeError("sealed v705 import protocol changed unexpectedly")
    source = source.replace(OLD_FBX, NEW_FBX)
    source = source.replace("v705", "v738").replace("V705", "V738")
    exec(compile(source, str(SOURCE) + "::v738", "exec"), {"__name__": "__main__"})


import_ururu_corrected_eyelid_morphs_v738()
