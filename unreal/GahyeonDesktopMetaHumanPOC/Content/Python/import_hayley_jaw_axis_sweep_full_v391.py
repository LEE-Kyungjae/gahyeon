"""Import the full-mesh jaw sweep while binding its animation to Hayley's skeleton."""

import json
from pathlib import Path

import unreal


SOURCE = Path(
    "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v390-hayley-jaw-axis-full/Hayley_JawAxisSweep_Full_v390.fbx"
)
SKELETON = "/Game/LivingCharacterPOC/v371/Characters/Hayley/Hayley2_Skeleton"
DESTINATION = "/Game/LivingCharacterPOC/v391/JawAxisSweepImport"
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v391-hayley-jaw-axis-import/report.json"
)


def import_hayley_jaw_axis_sweep_full_v391():
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    if REPORT.exists():
        raise RuntimeError(f"refusing to overwrite report: {REPORT}")
    if unreal.EditorAssetLibrary.does_directory_exist(DESTINATION):
        existing = unreal.EditorAssetLibrary.list_assets(DESTINATION, recursive=True)
        if existing:
            raise RuntimeError(f"refusing to overwrite full sweep import: {existing}")
    skeleton = unreal.load_asset(SKELETON)
    if skeleton is None:
        raise RuntimeError(f"Hayley skeleton unavailable: {SKELETON}")
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(SOURCE))
    task.set_editor_property("destination_path", DESTINATION)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", False)
    task.set_editor_property("save", True)
    options = unreal.FbxImportUI()
    options.set_editor_property("import_mesh", True)
    options.set_editor_property("import_as_skeletal", True)
    options.set_editor_property("import_materials", False)
    options.set_editor_property("import_textures", False)
    options.set_editor_property("import_animations", True)
    options.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH)
    options.set_editor_property("skeleton", skeleton)
    options.skeletal_mesh_import_data.set_editor_property("convert_scene", True)
    options.skeletal_mesh_import_data.set_editor_property("convert_scene_unit", True)
    options.anim_sequence_import_data.set_editor_property("import_bone_tracks", True)
    task.set_editor_property("options", options)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    imported = sorted(str(item) for item in task.get_editor_property("imported_object_paths"))
    animations = []
    for item in imported:
        asset = unreal.load_asset(item.split(".", 1)[0])
        if isinstance(asset, unreal.AnimSequence):
            animations.append(item.split(".", 1)[0])
    if len(animations) != 1:
        raise RuntimeError(f"expected one jaw sweep animation, got {animations}; all={imported}")
    report = {
        "schemaVersion": 1,
        "iteration": "v391",
        "status": "draft-full-mesh-jaw-axis-sweep-imported",
        "source": str(SOURCE),
        "targetSkeleton": SKELETON,
        "importedObjects": imported,
        "importedAnimation": animations[0],
        "visualValidationPending": True,
        "humanApproved": False,
        "releaseEligible": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("HAYLEY_V391_JAW_SWEEP=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


import_hayley_jaw_axis_sweep_full_v391()
