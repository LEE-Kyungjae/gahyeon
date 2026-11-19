"""Export the v043 body and official garment as immutable v048 conform sources."""

import json
from pathlib import Path

import unreal


OUTPUT_DIR = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/garment-conform/v048/source"
)
BODY_PATH = (
    "/Game/Gahyeon/CharacterPipeline/v027/AssembledMedium/Skotukeda_Medium_v027/"
    "Body/SKM_MHC_Skotukeda_Baseline_v026_BodyMesh"
)
GARMENT_PATH = (
    "/MetaHumanCharacter/Optional/Clothing/DefaultGarment/ClothAssets/"
    "bodyShapeC/Meshes/DG_bodyShapeCcombined"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
exports = {
    "body": (BODY_PATH, OUTPUT_DIR / "skotukeda-body-v048.fbx"),
    "garment": (GARMENT_PATH, OUTPUT_DIR / "default-garment-bodyshape-c-v048.fbx"),
}
manifest = {"schemaVersion": 1, "assets": {}}
for role, (asset_path, output_path) in exports.items():
    if output_path.exists():
        raise RuntimeError(f"refusing to overwrite conform source: {output_path}")
    asset = unreal.EditorAssetLibrary.load_asset(asset_path)
    if asset is None:
        raise RuntimeError(f"conform source asset is unavailable: {asset_path}")
    task = unreal.AssetExportTask()
    task.set_editor_property("object", asset)
    task.set_editor_property("filename", str(output_path))
    task.set_editor_property("automated", True)
    task.set_editor_property("prompt", False)
    task.set_editor_property("replace_identical", False)
    if not unreal.Exporter.run_asset_export_task(task):
        raise RuntimeError(f"failed to export {role}: {asset_path}")
    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise RuntimeError(f"exported {role} FBX is empty: {output_path}")
    manifest["assets"][role] = {
        "assetPath": asset_path,
        "file": str(output_path),
        "bytes": output_path.stat().st_size,
        "class": asset.get_class().get_name(),
    }

manifest_path = OUTPUT_DIR.parent / "source-manifest.json"
manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
unreal.log(f"Gahyeon v048 garment conform sources exported: {manifest_path}")
