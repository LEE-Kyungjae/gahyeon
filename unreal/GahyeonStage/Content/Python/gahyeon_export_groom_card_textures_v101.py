"""Export original and assembled Groom card atlases for channel-level QA."""

import hashlib
import json
from pathlib import Path

import unreal


ASSETS = {
    "assembled-coverage-depth-seed": (
        "/Game/Gahyeon/CharacterPipeline/v095/AssembledHigh/"
        "Skotukeda_WardrobeGroomHigh_v095/Grooms/Textures/"
        "Hair_L_StraightBangs_CardsAtlas_Attribute."
        "Hair_L_StraightBangs_CardsAtlas_Attribute"
    ),
    "source-rootuv-seed-coverage": (
        "/Game/Gahyeon/CharacterPipeline/v095/CommonHigh/Optional/Grooms/"
        "GroomAssets/Hair/Hair_L_StraightBangs/"
        "Hair_L_StraightBangs_RooUVSeedCoverage."
        "Hair_L_StraightBangs_RooUVSeedCoverage"
    ),
    "source-colorxy-depth-groupid": (
        "/Game/Gahyeon/CharacterPipeline/v095/CommonHigh/Optional/Grooms/"
        "GroomAssets/Hair/Hair_L_StraightBangs/"
        "Hair_L_StraightBangs_ColorXYDepthGroupID."
        "Hair_L_StraightBangs_ColorXYDepthGroupID"
    ),
    "source-tangent-coordu": (
        "/Game/Gahyeon/CharacterPipeline/v095/CommonHigh/Optional/Grooms/"
        "GroomAssets/Hair/Hair_L_StraightBangs/"
        "Hair_L_StraightBangs_TangentCoordU."
        "Hair_L_StraightBangs_TangentCoordU"
    ),
}
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v101-groom-card-texture-export"
)


def optional_property(owner, name):
    try:
        value = owner.get_editor_property(name)
        return str(value)
    except Exception as error:
        return {"unavailable": str(error)}


def export_groom_card_textures():
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to overwrite immutable v101 export: {OUTPUT}")
    OUTPUT.mkdir(parents=True, exist_ok=False)
    records = []
    for label, asset_path in ASSETS.items():
        texture = unreal.load_asset(asset_path)
        if texture is None:
            raise RuntimeError(f"texture unavailable: {asset_path}")
        destination = OUTPUT / f"{label}.png"
        task = unreal.AssetExportTask()
        task.set_editor_property("object", texture)
        task.set_editor_property("filename", str(destination))
        task.set_editor_property("automated", True)
        task.set_editor_property("prompt", False)
        task.set_editor_property("replace_identical", True)
        task.set_editor_property("exporter", unreal.TextureExporterPNG())
        if not unreal.Exporter.run_asset_export_task(task) or not destination.is_file():
            raise RuntimeError(f"failed to export texture: {asset_path}")
        records.append({
            "label": label,
            "asset": texture.get_path_name(),
            "file": str(destination),
            "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
            "sizeBytes": destination.stat().st_size,
            "sizeX": optional_property(texture, "blueprint_get_size_x"),
            "sizeY": optional_property(texture, "blueprint_get_size_y"),
            "compressionSettings": optional_property(texture, "compression_settings"),
            "srgb": optional_property(texture, "srgb"),
        })
    (OUTPUT / "export-report.json").write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v101",
        "state": "read-only-groom-card-texture-export",
        "textures": records,
        "automaticApproval": False,
        "productionReady": False,
    }, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v101 Groom card textures exported: {OUTPUT}")
    unreal.SystemLibrary.quit_editor()


export_groom_card_textures()
