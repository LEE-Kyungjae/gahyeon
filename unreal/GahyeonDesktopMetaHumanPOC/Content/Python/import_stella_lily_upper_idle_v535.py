"""Import Stella/Lily's foot-locked upper-body living-idle draft."""

import hashlib
import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE = ROOT / "artifacts/living-character-poc-v533-stella-lily-upper-idle/StellaLily_UpperIdle_v533.fbx"
SKELETON_PATH = "/Game/LivingCharacterPOC/v520/Characters/StellaLilyPreview/StellaLily_Modular_v518_Skeleton"
DESTINATION = "/Game/LivingCharacterPOC/v535/Animation"
REPORT = ROOT / "artifacts/living-character-poc-v535-stella-lily-upper-idle-import/report.json"


def import_stella_lily_upper_idle_v535():
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    if REPORT.exists() or unreal.EditorAssetLibrary.list_assets(DESTINATION, recursive=True):
        raise RuntimeError("refusing to overwrite immutable v535 outputs")
    skeleton = unreal.load_asset(SKELETON_PATH)
    if skeleton is None:
        raise RuntimeError(f"missing Stella/Lily skeleton: {SKELETON_PATH}")
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
    imported = sorted(str(value) for value in task.get_editor_property("imported_object_paths"))
    animations = []
    for object_path in imported:
        asset_path = object_path.split(".", 1)[0]
        if isinstance(unreal.load_asset(asset_path), unreal.AnimSequence):
            animations.append(asset_path)
    if len(animations) != 1:
        raise RuntimeError(f"expected one Stella/Lily idle, got {animations}; imported={imported}")
    animation = unreal.load_asset(animations[0])
    if animation.get_editor_property("skeleton") != skeleton:
        raise RuntimeError("Stella/Lily idle skeleton mismatch")
    report = {
        "schemaVersion": 1,
        "iteration": "v535",
        "status": "draft-upper-body-idle-imported",
        "source": str(SOURCE),
        "sourceSha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "skeleton": SKELETON_PATH,
        "animation": animations[0],
        "durationSeconds": float(animation.get_play_length()),
        "sampledKeys": int(animation.get_editor_property("number_of_sampled_keys")),
        "footLockPolicy": "target-lower-body-rest-pose",
        "humanApproved": False,
        "releaseEligible": False
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("STELLA_LILY_UPPER_IDLE_IMPORT=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


import_stella_lily_upper_idle_v535()
