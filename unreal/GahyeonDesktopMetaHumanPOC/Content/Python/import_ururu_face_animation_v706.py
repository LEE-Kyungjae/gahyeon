"""Import v688 Ururu facial curves as animation-only on the validated skeleton."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE = ROOT / "artifacts/living-character-poc-v688-ururu-centimeter-head-morphs/Ururu_HeadMorphs_Centimeter_v688.fbx"
SKELETON_PATH = "/Game/LivingCharacterPOC/v585/Characters/UruruCentimeterNormalized/Ururu_CentimeterNormalized_v584_Skeleton"
DESTINATION = "/Game/LivingCharacterPOC/v706/Animation/UruruFace"
REPORT = ROOT / "artifacts/living-character-poc-v706-ururu-face-animation-import/report.json"


def import_ururu_face_animation_v706():
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    if REPORT.exists() or unreal.EditorAssetLibrary.list_assets(DESTINATION, recursive=True):
        raise RuntimeError("refusing to overwrite immutable v706 output")
    skeleton = unreal.load_asset(SKELETON_PATH)
    if skeleton is None:
        raise RuntimeError(f"missing validated Ururu skeleton: {SKELETON_PATH}")
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(SOURCE))
    task.set_editor_property("destination_path", DESTINATION)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", False)
    task.set_editor_property("save", True)
    options = unreal.FbxImportUI()
    options.set_editor_property("import_mesh", False)
    options.set_editor_property("import_as_skeletal", True)
    options.set_editor_property("import_materials", False)
    options.set_editor_property("import_textures", False)
    options.set_editor_property("import_animations", True)
    options.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_ANIMATION)
    options.set_editor_property("skeleton", skeleton)
    options.anim_sequence_import_data.set_editor_property("convert_scene", True)
    options.anim_sequence_import_data.set_editor_property("convert_scene_unit", True)
    options.anim_sequence_import_data.set_editor_property("import_bone_tracks", True)
    task.set_editor_property("options", options)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

    paths = sorted(unreal.EditorAssetLibrary.list_assets(DESTINATION, recursive=True))
    animations = []
    for path in paths:
        asset = unreal.load_asset(path)
        if isinstance(asset, unreal.AnimSequence):
            if asset.get_editor_property("skeleton") != skeleton:
                raise RuntimeError(f"v706 animation skeleton mismatch: {path}")
            animations.append({
                "path": path.split(".", 1)[0],
                "playLengthSeconds": float(asset.get_play_length()),
                "numberOfSampledKeys": int(asset.get_number_of_sampled_keys()),
            })
            unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False)
    if not animations:
        raise RuntimeError(f"v706 produced no saved AnimSequence; assets={paths}")
    report = {
        "schemaVersion": 1,
        "iteration": "v706",
        "status": "imported-draft-ururu-face-animation-on-validated-skeleton",
        "source": str(SOURCE),
        "sourceSha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "skeleton": SKELETON_PATH,
        "animations": animations,
        "importedObjectsReportedByTask": sorted(str(path) for path in task.get_editor_property("imported_object_paths")),
        "visualValidationPending": True,
        "automaticApproval": False,
        "humanApproved": False,
        "productionReady": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.log("URURU_FACE_ANIMATION_IMPORT_V706=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


import_ururu_face_animation_v706()
