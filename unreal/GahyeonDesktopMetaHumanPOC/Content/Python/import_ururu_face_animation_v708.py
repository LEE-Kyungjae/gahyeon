"""Import the v688 Ururu facial curves as animation-only with FBX type detection disabled."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE = ROOT / "artifacts/living-character-poc-v688-ururu-centimeter-head-morphs/Ururu_HeadMorphs_Centimeter_v688.fbx"
SKELETON_PATH = "/Game/LivingCharacterPOC/v585/Characters/UruruCentimeterNormalized/Ururu_CentimeterNormalized_v584_Skeleton"
DESTINATION = "/Game/LivingCharacterPOC/v708/Animation/UruruFace"
REPORT = ROOT / "artifacts/living-character-poc-v708-ururu-face-animation-import/report.json"


def _data_model_stats(animation: unreal.AnimSequence) -> dict[str, int | float]:
    model = animation.get_editor_property("data_model_interface")
    if model is None:
        raise RuntimeError(f"AnimSequence has no animation data model: {animation.get_path_name()}")
    stats: dict[str, int | float] = {}
    for name in (
        "get_number_of_float_curves",
        "get_number_of_frames",
        "get_number_of_keys",
        "get_num_bone_tracks",
        "get_play_length",
    ):
        method = getattr(model, name, None)
        if callable(method):
            stats[name] = method()
    return stats


def import_ururu_face_animation_v708() -> None:
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    if REPORT.exists() or unreal.EditorAssetLibrary.list_assets(DESTINATION, recursive=True):
        raise RuntimeError("refusing to overwrite immutable v708 output")
    skeleton = unreal.load_asset(SKELETON_PATH)
    if skeleton is None:
        raise RuntimeError(f"missing validated Ururu skeleton: {SKELETON_PATH}")

    options = unreal.FbxImportUI()
    options.set_editor_property("automated_import_should_detect_type", False)
    options.set_editor_property("import_mesh", False)
    options.set_editor_property("import_as_skeletal", True)
    options.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_ANIMATION)
    options.set_editor_property("original_import_type", unreal.FBXImportType.FBXIT_ANIMATION)
    options.set_editor_property("import_materials", False)
    options.set_editor_property("import_textures", False)
    options.set_editor_property("import_animations", True)
    options.set_editor_property("skeleton", skeleton)
    options.anim_sequence_import_data.set_editor_property("convert_scene", True)
    options.anim_sequence_import_data.set_editor_property("convert_scene_unit", True)
    options.anim_sequence_import_data.set_editor_property("import_bone_tracks", True)

    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(SOURCE))
    task.set_editor_property("destination_path", DESTINATION)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", False)
    task.set_editor_property("save", False)
    task.set_editor_property("factory", unreal.FbxFactory())
    task.set_editor_property("options", options)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

    assets = []
    for path in sorted(unreal.EditorAssetLibrary.list_assets(DESTINATION, recursive=True)):
        asset = unreal.load_asset(path)
        record = {
            "path": path.split(".", 1)[0],
            "class": asset.get_class().get_name() if asset else None,
        }
        if isinstance(asset, unreal.AnimSequence):
            if asset.get_editor_property("skeleton") != skeleton:
                raise RuntimeError(f"animation skeleton mismatch: {path}")
            record["playLengthSeconds"] = float(asset.get_play_length())
            record["dataModelStats"] = _data_model_stats(asset)
            unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False)
        assets.append(record)

    animations = [asset for asset in assets if asset["class"] == "AnimSequence"]
    if not animations:
        raise RuntimeError(f"v708 produced no AnimSequence; assets={assets}")
    if any(asset["class"] == "SkeletalMesh" for asset in assets):
        raise RuntimeError(f"v708 unexpectedly imported a SkeletalMesh: {assets}")
    if max(asset["dataModelStats"].get("get_number_of_float_curves", 0) for asset in animations) < 4:
        raise RuntimeError(f"v708 AnimSequence lacks the four expected morph curves: {animations}")

    report = {
        "schemaVersion": 1,
        "iteration": "v708",
        "status": "validated-draft-animation-only-legacy-fbx-import",
        "source": str(SOURCE),
        "sourceSha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "skeleton": SKELETON_PATH,
        "assets": assets,
        "importedObjectsReportedByTask": sorted(str(path) for path in task.get_editor_property("imported_object_paths")),
        "automaticTypeDetection": False,
        "visualValidationPending": True,
        "automaticApproval": False,
        "humanApproved": False,
        "productionReady": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.log("URURU_FACE_ANIMATION_IMPORT_V708=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


import_ururu_face_animation_v708()
