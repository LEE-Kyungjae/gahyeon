"""Import the accessory-free Hayley face QA mesh onto the clean v448 skeleton."""

import hashlib
import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE = ROOT / "artifacts/living-character-poc-v474-hayley-face-qa-bind/Hayley_FaceQA_v474.fbx"
SKELETON_PATH = "/Game/LivingCharacterPOC/v448/Characters/HayleyBindClean/Hayley_BindPoseClean_v447_Skeleton"
DESTINATION = "/Game/LivingCharacterPOC/v475/Characters/HayleyFaceQA"
REPORT = ROOT / "artifacts/living-character-poc-v475-hayley-face-qa-import/report.json"


def import_hayley_face_qa_v475():
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    if REPORT.exists() or unreal.EditorAssetLibrary.list_assets(DESTINATION, recursive=True):
        raise RuntimeError("refusing to overwrite immutable v475 outputs")
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
    options.set_editor_property("import_mesh", True)
    options.set_editor_property("import_as_skeletal", True)
    options.set_editor_property("import_materials", True)
    options.set_editor_property("import_textures", True)
    options.set_editor_property("import_animations", False)
    options.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH)
    options.set_editor_property("skeleton", skeleton)
    options.skeletal_mesh_import_data.set_editor_property("convert_scene", True)
    options.skeletal_mesh_import_data.set_editor_property("convert_scene_unit", True)
    options.skeletal_mesh_import_data.set_editor_property("import_mesh_lo_ds", False)
    task.set_editor_property("options", options)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    imported = sorted(str(value) for value in task.get_editor_property("imported_object_paths"))
    meshes = []
    for object_path in imported:
        asset_path = object_path.split(".", 1)[0]
        asset = unreal.load_asset(asset_path)
        if isinstance(asset, unreal.SkeletalMesh):
            meshes.append(asset_path)
    if len(meshes) != 1:
        raise RuntimeError(f"expected one skeletal mesh, got {meshes}; imported={imported}")
    mesh = unreal.load_asset(meshes[0])
    if mesh.get_editor_property("skeleton") != skeleton:
        raise RuntimeError("face QA mesh imported against the wrong skeleton")
    report = {
        "schemaVersion": 1, "iteration": "v475", "status": "draft-face-qa-imported",
        "source": str(SOURCE), "sourceSha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "skeleton": SKELETON_PATH, "skeletalMesh": meshes[0], "importedObjects": imported,
        "excludedMeshes": ["Glasses", "Hat", "Earring"],
        "humanApproved": False, "releaseEligible": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("HAYLEY_FACE_QA_IMPORT=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


import_hayley_face_qa_v475()
