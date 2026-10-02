"""Import Ururu facial morphs through UE's legacy FBX path onto v585."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE = ROOT / "artifacts/living-character-poc-v688-ururu-centimeter-head-morphs/Ururu_HeadMorphs_Centimeter_v688.fbx"
SKELETON_PATH = "/Game/LivingCharacterPOC/v585/Characters/UruruCentimeterNormalized/Ururu_CentimeterNormalized_v584_Skeleton"
DESTINATION = "/Game/LivingCharacterPOC/v705/Characters/UruruFacial"
REPORT = ROOT / "artifacts/living-character-poc-v705-ururu-animated-head-morph-import/report.json"
REQUIRED = {"EyeBlink_L", "EyeBlink_R", "GazeLeft", "GazeRight"}


def import_ururu_animated_head_morphs_v705() -> dict[str, object]:
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    if REPORT.exists() or unreal.EditorAssetLibrary.list_assets(DESTINATION, recursive=True):
        raise RuntimeError("refusing to overwrite immutable v705 output")
    skeleton = unreal.load_asset(SKELETON_PATH)
    if skeleton is None:
        raise RuntimeError(f"missing validated Ururu skeleton: {SKELETON_PATH}")

    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(SOURCE))
    task.set_editor_property("destination_path", DESTINATION)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", False)
    task.set_editor_property("replace_existing_settings", False)
    task.set_editor_property("save", True)

    options = unreal.FbxImportUI()
    options.set_editor_property("import_mesh", True)
    options.set_editor_property("import_as_skeletal", True)
    options.set_editor_property("import_materials", True)
    options.set_editor_property("import_textures", True)
    options.set_editor_property("import_animations", True)
    options.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH)
    options.set_editor_property("skeleton", skeleton)
    options.skeletal_mesh_import_data.set_editor_property("convert_scene", True)
    options.skeletal_mesh_import_data.set_editor_property("convert_scene_unit", True)
    options.skeletal_mesh_import_data.set_editor_property("import_morph_targets", True)
    options.skeletal_mesh_import_data.set_editor_property("update_skeleton_reference_pose", False)
    options.skeletal_mesh_import_data.set_editor_property("use_t0_as_ref_pose", False)
    task.set_editor_property("options", options)

    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    imported = sorted(str(value) for value in task.get_editor_property("imported_object_paths"))
    meshes = []
    animations = []
    for object_path in imported:
        path = object_path.split(".", 1)[0]
        asset = unreal.load_asset(path)
        if isinstance(asset, unreal.SkeletalMesh):
            meshes.append(path)
        elif isinstance(asset, unreal.AnimSequence):
            animations.append(path)
    if len(meshes) != 1:
        raise RuntimeError(f"expected one v705 mesh, got {meshes}; imported={imported}")
    if not animations:
        raise RuntimeError("animated v688 FBX produced no AnimSequence")

    mesh = unreal.load_asset(meshes[0])
    actual_skeleton = mesh.get_editor_property("skeleton")
    if actual_skeleton != skeleton:
        raise RuntimeError(
            "legacy FBX import rejected validated skeleton: "
            f"expected={SKELETON_PATH}, actual={actual_skeleton.get_path_name() if actual_skeleton else None}"
        )
    morphs = sorted(str(name) for name in mesh.get_all_morph_target_names())
    missing = sorted(REQUIRED - set(morphs))
    if missing:
        raise RuntimeError(f"legacy import lost required morphs: {missing}; actual={morphs}")
    animation_details = []
    for path in animations:
        animation = unreal.load_asset(path)
        actual_animation_skeleton = animation.get_editor_property("skeleton")
        if actual_animation_skeleton != skeleton:
            raise RuntimeError(
                f"v705 animation skeleton mismatch: animation={path}, "
                f"actual={actual_animation_skeleton.get_path_name() if actual_animation_skeleton else None}"
            )
        animation_details.append({
            "path": path,
            "skeleton": SKELETON_PATH,
            "playLengthSeconds": float(animation.get_play_length()),
        })

    report = {
        "schemaVersion": 1,
        "iteration": "v705",
        "status": "draft-legacy-fbx-animated-ururu-facial-morphs-on-validated-skeleton",
        "source": str(SOURCE),
        "sourceSha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "skeletalMesh": meshes[0],
        "skeleton": SKELETON_PATH,
        "morphTargets": morphs,
        "requiredMorphTargets": sorted(REQUIRED),
        "animations": animation_details,
        "importedObjects": imported,
        "importer": "legacy-fbx",
        "fbxAnimationImported": True,
        "visualValidationPending": True,
        "automaticApproval": False,
        "humanApproved": False,
        "productionReady": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.log("URURU_ANIMATED_HEAD_MORPH_IMPORT_V705=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()
    return report


REPORT_VALUE = import_ururu_animated_head_morphs_v705()
