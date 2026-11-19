"""Import clean Hayley blink/smile tracks onto the v448 skeleton."""

import hashlib
import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE = ROOT / "artifacts/living-character-poc-v468-hayley-clean-expression-calibration/Hayley_CleanExpressionCalibration_v468.fbx"
SKELETON_PATH = "/Game/LivingCharacterPOC/v448/Characters/HayleyBindClean/Hayley_BindPoseClean_v447_Skeleton"
DESTINATION = "/Game/LivingCharacterPOC/v469/Animation"
REPORT = ROOT / "artifacts/living-character-poc-v469-hayley-clean-expression-import/report.json"


def import_hayley_clean_expression_v469():
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    if REPORT.exists():
        raise FileExistsError(REPORT)
    existing = unreal.EditorAssetLibrary.list_assets(DESTINATION, recursive=True)
    if existing:
        raise RuntimeError(f"refusing to overwrite expression assets: {existing}")
    skeleton = unreal.load_asset(SKELETON_PATH)
    if skeleton is None:
        raise RuntimeError(f"missing clean Hayley skeleton: {SKELETON_PATH}")

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
    imported = sorted(str(path) for path in task.get_editor_property("imported_object_paths"))
    animations = [
        str(path).split(".", 1)[0] for path in imported
        if isinstance(unreal.load_asset(str(path).split(".", 1)[0]), unreal.AnimSequence)
    ]
    if len(animations) != 1:
        raise RuntimeError(f"expected one expression animation, got {animations}; imported={imported}")
    animation = unreal.load_asset(animations[0])
    if animation.get_editor_property("skeleton") != skeleton:
        raise RuntimeError("expression animation imported against the wrong skeleton")
    report = {
        "schemaVersion": 1,
        "iteration": "v469",
        "status": "draft-clean-expression-imported",
        "source": str(SOURCE),
        "sourceSha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "skeleton": SKELETON_PATH,
        "animation": animations[0],
        "importedObjects": imported,
        "poses": {"neutral": 1, "blink": 11, "neutralAfterBlink": 21, "smile": 31, "neutralReturn": 41},
        "humanApproved": False,
        "releaseEligible": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("HAYLEY_CLEAN_EXPRESSION_IMPORT=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


import_hayley_clean_expression_v469()
