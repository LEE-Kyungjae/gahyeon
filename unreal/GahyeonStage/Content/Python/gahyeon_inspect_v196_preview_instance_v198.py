"""Locate v196 transient face/body meshes and preview-instance data without saving."""

import json
from pathlib import Path

import unreal


CHARACTER = "/Game/Gahyeon/CharacterPipeline/v196/Character/MHC_Gahyeon_KeenTools_Cm_v196"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v198-metahuman-preview-instance-inspection/report.json"
)


def inspect_v196_preview_instance_v198():
    if OUTPUT.exists():
        raise RuntimeError("refusing to overwrite immutable v198 inspection")
    character = unreal.load_asset(CHARACTER)
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    if character is None or not subsystem.try_add_object_to_edit(character):
        raise RuntimeError("failed to initialize v196 preview state")
    try:
        collection = subsystem.get_preview_collection(character)
        instance = collection.default_instance
        item_records = []
        for key in collection.get_all_item_keys():
            item_records.append({
                "key": str(key),
                "displayName": str(collection.get_item_display_name(key)),
                "slot": str(collection.get_item_slot_name(key)),
            })
        transient_meshes = []
        iterator_error = None
        try:
            for mesh in unreal.ObjectIterator(unreal.SkeletalMesh):
                path = mesh.get_path_name()
                if "/Engine/Transient" in path or "MetaHumanCharacterEditorSubsystem" in path:
                    bounds = mesh.get_imported_bounds()
                    transient_meshes.append({
                        "path": path,
                        "name": mesh.get_name(),
                        "origin": [bounds.origin.x, bounds.origin.y, bounds.origin.z],
                        "extent": [bounds.box_extent.x, bounds.box_extent.y, bounds.box_extent.z],
                    })
        except Exception as error:
            iterator_error = str(error)
        report = {
            "previewCollection": collection.get_path_name(),
            "previewInstanceClass": instance.get_class().get_name(),
            "previewInstancePath": instance.get_path_name(),
            "previewInstanceMembers": sorted(
                name for name in dir(instance) if not name.startswith("_")
            ),
            "items": item_records,
            "transientSkeletalMeshes": transient_meshes,
            "iteratorError": iterator_error,
            "unrealModuleCandidates": sorted(
                name for name in dir(unreal)
                if "iterator" in name.lower() or "object" in name.lower()
            ),
        }
    finally:
        if subsystem.is_object_added_for_editing(character):
            subsystem.remove_object_to_edit(character)
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v198",
        "state": "read-only-preview-instance-inspection",
        "character": CHARACTER,
        "inspection": report,
    }, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v198 preview instance inspection complete: {OUTPUT}")
    unreal.SystemLibrary.quit_editor()


inspect_v196_preview_instance_v198()
