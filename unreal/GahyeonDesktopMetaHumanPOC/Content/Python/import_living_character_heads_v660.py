"""Import immutable Stella/Lily and Ururu neutral-head conform inputs into UE 5.8."""

import hashlib
import json
from pathlib import Path

import unreal


SOURCE_ROOT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/"
    "living-character-poc-v659-unreal-axis-heads"
)
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/"
    "living-character-poc-v660-unreal-neutral-head-import/report.json"
)
TARGET_ROOT = "/Game/LivingCharacterPOC/v660/Input"
HEADS = (
    {
        "id": "stella-lily",
        "source": SOURCE_ROOT / "stella-lily-neutral-head-v659.fbx",
        "assetName": "SM_StellaLily_UEAxisHead_v660",
        "expectedSha256": "2fd287984081f62e255cccd9921fb94dc7d89e1a7720e1e08d7d04fab3b2fd7b",
    },
    {
        "id": "ururu",
        "source": SOURCE_ROOT / "ururu-neutral-head-v659.fbx",
        "assetName": "SM_Ururu_UEAxisHead_v660",
        "expectedSha256": "28910ddc9790d1600022097f25b45682910f50f427274d2d612a847efd605210",
    },
)


def sha256_file_v660(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bounds_record_v660(bounds):
    origin = bounds.origin
    extent = bounds.box_extent
    return {
        "originCm": [origin.x, origin.y, origin.z],
        "extentCm": [extent.x, extent.y, extent.z],
        "dimensionsCm": [extent.x * 2.0, extent.y * 2.0, extent.z * 2.0],
    }


def import_head_v660(record):
    source = record["source"]
    digest = sha256_file_v660(source) if source.is_file() else None
    if digest != record["expectedSha256"]:
        raise RuntimeError(f"sealed v650 source mismatch for {record['id']}: {digest}")
    asset_path = f"{TARGET_ROOT}/{record['assetName']}"
    if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        raise RuntimeError(f"refusing to overwrite immutable v660 asset: {asset_path}")

    task = unreal.AssetImportTask()
    task.filename = str(source)
    task.destination_path = TARGET_ROOT
    task.destination_name = record["assetName"]
    task.automated = True
    task.replace_existing = False
    task.save = True
    options = unreal.FbxImportUI()
    options.import_mesh = True
    options.import_as_skeletal = False
    options.import_materials = False
    options.import_textures = False
    options.static_mesh_import_data.combine_meshes = True
    options.static_mesh_import_data.convert_scene = True
    options.static_mesh_import_data.convert_scene_unit = True
    options.static_mesh_import_data.import_uniform_scale = 1.0
    task.options = options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

    mesh = unreal.load_asset(asset_path)
    if mesh is None or mesh.get_class().get_name() != "StaticMesh":
        raise RuntimeError(f"v660 import failed for {record['id']}: {task.imported_object_paths}")
    bounds = bounds_record_v660(mesh.get_bounds())
    dimensions = bounds["dimensionsCm"]
    if not (10.0 <= min(dimensions) and max(dimensions) <= 40.0):
        raise RuntimeError(f"implausible neutral-head size for {record['id']}: {bounds}")
    if not 100.0 <= bounds["originCm"][2] <= 180.0:
        raise RuntimeError(f"head is not upright on the UE Z axis for {record['id']}: {bounds}")
    if not unreal.EditorAssetLibrary.save_asset(asset_path, only_if_is_dirty=False):
        raise RuntimeError(f"failed to save v660 mesh: {asset_path}")
    return {
        "id": record["id"],
        "source": {"path": str(source), "sha256": digest},
        "asset": asset_path,
        "class": mesh.get_class().get_name(),
        "bounds": bounds,
    }


def import_living_character_heads_v660():
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to overwrite immutable v660 report: {OUTPUT}")
    imported = [import_head_v660(record) for record in HEADS]
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "iteration": "v660",
                "state": "ue-axis-baked-neutral-heads-imported-awaiting-conform",
                "engine": "5.8",
                "characters": imported,
                "role": "shape-reference-and-metahuman-conform-input-only",
                "finalProductionTopology": False,
                "automaticApproval": False,
                "productionReady": False,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    unreal.log(f"Living character v660 import complete: {OUTPUT}")
    unreal.SystemLibrary.quit_editor()


import_living_character_heads_v660()
