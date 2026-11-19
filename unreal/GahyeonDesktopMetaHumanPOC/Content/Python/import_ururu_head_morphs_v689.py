"""Import centimeter-normalized Ururu facial Morph Targets on the v585 skeleton."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE = ROOT / "artifacts/living-character-poc-v688-ururu-centimeter-head-morphs/Ururu_HeadMorphs_Centimeter_v688.fbx"
SKELETON_PATH = "/Game/LivingCharacterPOC/v585/Characters/UruruCentimeterNormalized/Ururu_CentimeterNormalized_v584_Skeleton"
DESTINATION = "/Game/LivingCharacterPOC/v689/Characters/UruruFacial"
REPORT = ROOT / "artifacts/living-character-poc-v689-ururu-head-morph-import/report.json"
REQUIRED_MORPHS = {"EyeBlink_L", "EyeBlink_R", "GazeLeft", "GazeRight"}


def morph_names(mesh: unreal.SkeletalMesh) -> list[str]:
    getter = getattr(mesh, "get_morph_targets", None)
    if callable(getter):
        return sorted(target.get_name() for target in getter())
    targets = mesh.get_editor_property("morph_targets")
    return sorted(target.get_name() for target in targets)


def import_ururu_head_morphs_v689() -> dict[str, object]:
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    if REPORT.exists() or unreal.EditorAssetLibrary.list_assets(DESTINATION, recursive=True):
        raise RuntimeError("refusing to overwrite immutable v689 output")
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
    task.set_editor_property("options", options)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

    imported = sorted(str(value) for value in task.get_editor_property("imported_object_paths"))
    meshes = []
    animations = []
    for object_path in imported:
        asset_path = object_path.split(".", 1)[0]
        asset = unreal.load_asset(asset_path)
        if isinstance(asset, unreal.SkeletalMesh):
            meshes.append(asset_path)
        elif isinstance(asset, unreal.AnimSequence):
            animations.append(asset_path)
    if len(meshes) != 1:
        raise RuntimeError(f"expected one v689 Ururu facial mesh, got {meshes}; imported={imported}")
    mesh = unreal.load_asset(meshes[0])
    actual_skeleton = mesh.get_editor_property("skeleton")
    if actual_skeleton != skeleton:
        raise RuntimeError(
            "v689 facial mesh rejected the validated skeleton: "
            f"expected={SKELETON_PATH}, actual={actual_skeleton.get_path_name() if actual_skeleton else None}"
        )
    names = morph_names(mesh)
    missing = sorted(REQUIRED_MORPHS - set(names))
    if missing:
        raise RuntimeError(f"UE import lost required Ururu morph targets: {missing}; actual={names}")
    report = {
        "schemaVersion": 1,
        "iteration": "v689",
        "status": "draft-ururu-facial-morphs-imported-on-validated-skeleton",
        "source": str(SOURCE),
        "sourceSha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "skeletalMesh": meshes[0],
        "skeleton": SKELETON_PATH,
        "morphTargets": names,
        "requiredMorphTargets": sorted(REQUIRED_MORPHS),
        "animations": animations,
        "importedObjects": imported,
        "visualValidationPending": True,
        "automaticApproval": False,
        "humanApproved": False,
        "productionReady": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.log("URURU_HEAD_MORPH_IMPORT_V689=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()
    return report


REPORT_VALUE = import_ururu_head_morphs_v689()
