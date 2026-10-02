"""Import the v388 animation-only jaw-axis sweep onto Hayley's UE skeleton."""

import json
from pathlib import Path

import unreal


SOURCE = Path(
    "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v388-hayley-jaw-axis/Hayley_JawAxisSweep_v388.fbx"
)
SKELETON = "/Game/LivingCharacterPOC/v371/Characters/Hayley/Hayley2_Skeleton"
DESTINATION = "/Game/LivingCharacterPOC/v389/Animation"
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v389-hayley-jaw-axis-import/report.json"
)


def import_hayley_jaw_axis_sweep_v389():
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    if REPORT.exists():
        raise RuntimeError(f"refusing to overwrite report: {REPORT}")
    if unreal.EditorAssetLibrary.does_directory_exist(DESTINATION):
        existing = unreal.EditorAssetLibrary.list_assets(DESTINATION, recursive=True)
        if existing:
            raise RuntimeError(f"refusing to overwrite imported sweep: {existing}")
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
    options.set_editor_property("import_mesh", False)
    options.set_editor_property("import_animations", True)
    options.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_ANIMATION)
    options.set_editor_property("skeleton", skeleton)
    options.anim_sequence_import_data.set_editor_property("import_bone_tracks", True)
    options.anim_sequence_import_data.set_editor_property("convert_scene", True)
    options.anim_sequence_import_data.set_editor_property("convert_scene_unit", True)
    task.set_editor_property("options", options)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    imported = sorted(str(item) for item in task.get_editor_property("imported_object_paths"))
    if len(imported) != 1:
        raise RuntimeError(f"expected one imported jaw sweep, got: {imported}")
    report = {
        "schemaVersion": 1,
        "iteration": "v389",
        "status": "draft-animation-only-jaw-axis-sweep-imported",
        "source": str(SOURCE),
        "targetSkeleton": SKELETON,
        "importedAnimation": imported[0].split(".", 1)[0],
        "visualValidationPending": True,
        "humanApproved": False,
        "releaseEligible": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("HAYLEY_V389_JAW_SWEEP=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


import_hayley_jaw_axis_sweep_v389()
