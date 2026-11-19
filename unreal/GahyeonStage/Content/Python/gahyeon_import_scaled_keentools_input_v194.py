"""Import the sealed v181 KeenTools target at its authored centimetre scale."""

import hashlib
import json
from pathlib import Path

import unreal


SOURCE = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v181-keentools-metahuman-input/gahyeon-keentools-skin-target-v181.fbx"
)
TARGET_ROOT = "/Game/Gahyeon/CharacterPipeline/v194/Input"
TARGET_MESH = f"{TARGET_ROOT}/SM_Gahyeon_KeenTools_Cm_v194"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v194-keentools-centimetre-import/report.json"
)


def bounds_record_v194(bounds):
    origin = bounds.origin
    extent = bounds.box_extent
    return {
        "origin": [origin.x, origin.y, origin.z],
        "extent": [extent.x, extent.y, extent.z],
        "dimensionsCm": [extent.x * 2.0, extent.y * 2.0, extent.z * 2.0],
    }


def import_scaled_keentools_input_v194():
    if OUTPUT.exists() or unreal.EditorAssetLibrary.does_asset_exist(TARGET_MESH):
        raise RuntimeError("refusing to overwrite immutable v194 import")
    if not SOURCE.is_file():
        raise RuntimeError(f"sealed v181 FBX missing: {SOURCE}")
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(SOURCE))
    task.set_editor_property("destination_path", TARGET_ROOT)
    task.set_editor_property("destination_name", "SM_Gahyeon_KeenTools_Cm_v194")
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", False)
    task.set_editor_property("save", True)
    options = unreal.FbxImportUI()
    options.set_editor_property("import_mesh", True)
    options.set_editor_property("import_as_skeletal", False)
    options.set_editor_property("import_materials", False)
    options.set_editor_property("import_textures", False)
    data = options.static_mesh_import_data
    data.set_editor_property("combine_meshes", True)
    data.set_editor_property("convert_scene", True)
    data.set_editor_property("convert_scene_unit", True)
    data.set_editor_property("import_uniform_scale", 0.01)
    task.set_editor_property("options", options)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh = unreal.load_asset(TARGET_MESH)
    if mesh is None:
        raise RuntimeError(f"corrected import failed: {task.imported_object_paths}")
    bounds = bounds_record_v194(mesh.get_bounds())
    dimensions = bounds["dimensionsCm"]
    if not 35.0 <= max(dimensions) <= 45.0:
        raise RuntimeError(f"corrected import violates 35-45cm head contract: {dimensions}")
    if not unreal.EditorAssetLibrary.save_asset(TARGET_MESH, only_if_is_dirty=False):
        raise RuntimeError("failed to save corrected v194 target")
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v194",
        "state": "centimetre-scale-target-validated-awaiting-conform",
        "source": {"path": str(SOURCE), "sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest()},
        "importUniformScale": 0.01,
        "targetMesh": TARGET_MESH,
        "bounds": bounds,
        "automaticApproval": False,
        "productionReady": False,
    }, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v194 corrected import complete: {OUTPUT}")
    unreal.SystemLibrary.quit_editor()


import_scaled_keentools_input_v194()
