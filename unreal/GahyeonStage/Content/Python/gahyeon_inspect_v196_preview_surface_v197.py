"""Inspect non-mutating UE 5.8 preview surfaces exposed for conformed v196."""

import json
from pathlib import Path

import unreal


CHARACTER = "/Game/Gahyeon/CharacterPipeline/v196/Character/MHC_Gahyeon_KeenTools_Cm_v196"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v197-metahuman-preview-surface-inspection/report.json"
)


def _public_members(value):
    return sorted(name for name in dir(value) if not name.startswith("_"))


def inspect_v196_preview_surface_v197():
    if OUTPUT.exists():
        raise RuntimeError("refusing to overwrite immutable v197 inspection")
    character = unreal.load_asset(CHARACTER)
    if character is None or character.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError(f"missing v196 MetaHuman Character: {CHARACTER}")
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    if not subsystem.try_add_object_to_edit(character):
        raise RuntimeError("failed to open v196 for read-only preview inspection")
    try:
        collection = subsystem.get_preview_collection(character)
        records = {
            "characterMembers": _public_members(character),
            "subsystemMembers": [
                name for name in _public_members(subsystem)
                if any(token in name.lower() for token in ("preview", "mesh", "face", "body"))
            ],
            "previewCollection": None,
        }
        if collection is not None:
            records["previewCollection"] = {
                "class": collection.get_class().get_name(),
                "path": collection.get_path_name(),
                "members": _public_members(collection),
            }
        for property_name in (
            "face_mesh", "body_mesh", "preview_face_mesh", "preview_body_mesh",
            "internal_collection", "face_state", "body_state"
        ):
            try:
                value = character.get_editor_property(property_name)
                records[f"property:{property_name}"] = (
                    value.get_path_name() if hasattr(value, "get_path_name") else str(value)
                )
            except Exception as error:
                records[f"property:{property_name}"] = f"ERROR: {error}"
    finally:
        if subsystem.is_object_added_for_editing(character):
            subsystem.remove_object_to_edit(character)
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v197",
        "state": "read-only-preview-surface-inspection",
        "character": CHARACTER,
        "inspection": records,
    }, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v197 preview inspection complete: {OUTPUT}")
    unreal.SystemLibrary.quit_editor()


inspect_v196_preview_surface_v197()
