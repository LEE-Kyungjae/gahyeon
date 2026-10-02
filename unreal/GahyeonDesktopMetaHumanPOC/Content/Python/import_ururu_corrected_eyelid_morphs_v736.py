"""Import v733 corrected eyelids with an explicit skeletal-FBX contract."""

from __future__ import annotations

from pathlib import Path


SOURCE = Path(__file__).with_name("import_ururu_animated_head_morphs_v705.py")
OLD_FBX = "artifacts/living-character-poc-v688-ururu-centimeter-head-morphs/Ururu_HeadMorphs_Centimeter_v688.fbx"
NEW_FBX = "artifacts/living-character-poc-v733-ururu-corrected-eyelid-winding/Ururu_HeadMorphs_CorrectedEyelids_v733.fbx"
TYPE_ANCHOR = "    options = unreal.FbxImportUI()\n"
TYPE_OVERRIDE = (
    TYPE_ANCHOR
    + "    options.set_editor_property(\"automated_import_should_detect_type\", False)\n"
    + "    options.set_editor_property(\"original_import_type\", unreal.FBXImportType.FBXIT_SKELETAL_MESH)\n"
)


def import_ururu_corrected_eyelid_morphs_v736() -> None:
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    source = SOURCE.read_text(encoding="utf-8")
    if source.count("v705") < 8 or OLD_FBX not in source:
        raise RuntimeError("sealed v705 import protocol changed unexpectedly")
    if source.count(TYPE_ANCHOR) != 1:
        raise RuntimeError("sealed v705 FBX type anchor changed unexpectedly")
    source = source.replace(OLD_FBX, NEW_FBX)
    source = source.replace(TYPE_ANCHOR, TYPE_OVERRIDE)
    source = source.replace("v705", "v736").replace("V705", "V736")
    exec(compile(source, str(SOURCE) + "::v736", "exec"), {"__name__": "__main__"})


import_ururu_corrected_eyelid_morphs_v736()
