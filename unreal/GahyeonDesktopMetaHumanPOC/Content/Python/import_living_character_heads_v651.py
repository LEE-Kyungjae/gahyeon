"""Import immutable Stella/Lily and Ururu neutral-head conform inputs into UE 5.8."""

import hashlib
import json
from pathlib import Path

import unreal


SOURCE_ROOT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/"
    "living-character-poc-v650-neutral-head-conform-inputs"
)
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/"
    "living-character-poc-v651-unreal-neutral-head-import/report.json"
)
TARGET_ROOT = "/Game/LivingCharacterPOC/v651/Input"
HEADS = (
    {
        "id": "stella-lily",
        "source": SOURCE_ROOT / "stella-lily-neutral-head-v650.obj",
        "assetName": "SM_StellaLily_NeutralHead_v651",
        "expectedSha256": "85c77ea09acc1be198722663e460847ead3ae489602b1ff93c048ee6e6c5129e",
    },
    {
        "id": "ururu",
        "source": SOURCE_ROOT / "ururu-neutral-head-v650.obj",
        "assetName": "SM_Ururu_NeutralHead_v651",
        "expectedSha256": "a093f80c184d87bc6a780945b788f0322819bbde893ac0ffcde75c105ad0e51f",
    },
)


def sha256_file_v651(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bounds_record_v651(bounds):
    origin = bounds.origin
    extent = bounds.box_extent
    return {
        "originCm": [origin.x, origin.y, origin.z],
        "extentCm": [extent.x, extent.y, extent.z],
        "dimensionsCm": [extent.x * 2.0, extent.y * 2.0, extent.z * 2.0],
    }


def import_head_v651(record):
    source = record["source"]
    digest = sha256_file_v651(source) if source.is_file() else None
    if digest != record["expectedSha256"]:
        raise RuntimeError(f"sealed v650 source mismatch for {record['id']}: {digest}")
    asset_path = f"{TARGET_ROOT}/{record['assetName']}"
    if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        raise RuntimeError(f"refusing to overwrite immutable v651 asset: {asset_path}")

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
    options.static_mesh_import_data.convert_scene = False
    options.static_mesh_import_data.convert_scene_unit = False
    options.static_mesh_import_data.import_uniform_scale = 1.0
    task.options = options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

    mesh = unreal.load_asset(asset_path)
    if mesh is None or mesh.get_class().get_name() != "StaticMesh":
        raise RuntimeError(f"v651 import failed for {record['id']}: {task.imported_object_paths}")
    bounds = bounds_record_v651(mesh.get_bounds())
    dimensions = bounds["dimensionsCm"]
    if not 10.0 <= max(dimensions) <= 40.0:
        raise RuntimeError(f"implausible neutral-head size for {record['id']}: {bounds}")
    if not unreal.EditorAssetLibrary.save_asset(asset_path, only_if_is_dirty=False):
        raise RuntimeError(f"failed to save v651 mesh: {asset_path}")
    return {
        "id": record["id"],
        "source": {"path": str(source), "sha256": digest},
        "asset": asset_path,
        "class": mesh.get_class().get_name(),
        "bounds": bounds,
    }


def import_living_character_heads_v651():
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to overwrite immutable v651 report: {OUTPUT}")
    imported = [import_head_v651(record) for record in HEADS]
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "iteration": "v651",
                "state": "neutral-heads-imported-awaiting-fixed-camera-preflight",
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
    unreal.log(f"Living character v651 import complete: {OUTPUT}")
    unreal.SystemLibrary.quit_editor()


import_living_character_heads_v651()
