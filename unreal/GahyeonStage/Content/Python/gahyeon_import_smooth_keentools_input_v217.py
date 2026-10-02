"""Import the immutable v216 smooth-normal target at centimetre scale."""

import hashlib
import json
from pathlib import Path

import unreal


SOURCE = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v216-keentools-smooth-head-input/gahyeon-keentools-smooth-head-target-v216.fbx"
)
TARGET_ROOT = "/Game/Gahyeon/CharacterPipeline/v217/Input"
TARGET_MESH = f"{TARGET_ROOT}/SM_Gahyeon_KeenTools_SmoothHead_Cm_v217"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v217-keentools-smooth-head-centimetre-import/report.json"
)


def bounds_record(bounds):
    origin = bounds.origin
    extent = bounds.box_extent
    return {
        "origin": [origin.x, origin.y, origin.z],
        "extent": [extent.x, extent.y, extent.z],
        "dimensionsCm": [extent.x * 2.0, extent.y * 2.0, extent.z * 2.0],
    }


def import_smooth_keentools_input_v217():
    if OUTPUT.exists() or unreal.EditorAssetLibrary.does_asset_exist(TARGET_MESH):
        raise RuntimeError("refusing to overwrite immutable v217 import")
    if not SOURCE.is_file():
        raise RuntimeError(f"sealed v216 FBX missing: {SOURCE}")
    task = unreal.AssetImportTask()
    task.filename = str(SOURCE)
    task.destination_path = TARGET_ROOT
    task.destination_name = "SM_Gahyeon_KeenTools_SmoothHead_Cm_v217"
    task.automated = True
    task.replace_existing = False
    task.save = True
    options = unreal.FbxImportUI()
    options.import_mesh = True
    options.import_as_skeletal = False
    options.import_materials = False
    options.import_textures = False
    data = options.static_mesh_import_data
    data.combine_meshes = True
    data.convert_scene = True
    data.convert_scene_unit = True
    data.import_uniform_scale = 0.01
    data.normal_import_method = (
        unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    )
    task.options = options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh = unreal.load_asset(TARGET_MESH)
    if mesh is None:
        raise RuntimeError(f"v217 import failed: {task.imported_object_paths}")
    bounds = bounds_record(mesh.get_bounds())
    if not 35.0 <= max(bounds["dimensionsCm"]) <= 45.0:
        raise RuntimeError(f"v217 centimetre contract failed: {bounds}")
    if not unreal.EditorAssetLibrary.save_asset(TARGET_MESH, only_if_is_dirty=False):
        raise RuntimeError("failed to save v217 target")
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    payload = {
        "schemaVersion": 1,
        "iteration": "v217",
        "state": "smooth-normal-centimetre-target-awaiting-tracker-portrait-qa",
        "source": {
            "path": str(SOURCE),
            "sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        },
        "importUniformScale": 0.01,
        "normalImportMethod": "IMPORT_NORMALS_AND_TANGENTS",
        "targetMesh": TARGET_MESH,
        "bounds": bounds,
        "automaticApproval": False,
        "productionReady": False,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v217 import complete: {OUTPUT}")
    unreal.SystemLibrary.quit_editor()


import_smooth_keentools_input_v217()
