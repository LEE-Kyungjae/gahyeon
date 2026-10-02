"""Clean-load and record the saved optimized v024 MetaHuman assembly."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import unreal


BUILD_ROOT = "/Game/Gahyeon/CharacterPipeline/v024/Assembled"
BLUEPRINT_PATH = (
    BUILD_ROOT
    + "/Gahyeon_CoarsePOC_v024/BP_Gahyeon_CoarsePOC_v024"
)


def validate():
    workspace = Path(os.environ.get("GAHYEON_WORKSPACE", "/Users/ze/work/gahyeonbot"))
    receipt_path = workspace / "artifacts/gahyeon-ch/metahuman-coarse-poc-v024-assembly.json"
    if receipt_path.exists():
        raise RuntimeError(f"refusing to overwrite immutable assembly receipt: {receipt_path}")
    blueprint = unreal.EditorAssetLibrary.load_asset(BLUEPRINT_PATH)
    if blueprint is None or blueprint.get_class().get_name() != "Blueprint":
        raise RuntimeError(f"assembled Blueprint failed clean reload: {BLUEPRINT_PATH}")
    assembled_assets = list(
        unreal.EditorAssetLibrary.list_assets(BUILD_ROOT, recursive=True, include_folder=False)
    )
    if len(assembled_assets) < 2:
        raise RuntimeError("assembled asset set is incomplete")

    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "observedAt": datetime.now(timezone.utc).isoformat(),
                "iteration": "v024",
                "engine": "Unreal Engine 5.8",
                "buildRoot": BUILD_ROOT,
                "blueprintAsset": BLUEPRINT_PATH,
                "pipelineType": "OPTIMIZED",
                "pipelineQuality": "LOW",
                "animationSystem": "AnimBP",
                "cleanReloadVerified": True,
                "assembledAssetCount": len(assembled_assets),
                "assembledAssets": [str(asset) for asset in assembled_assets],
                "qualityStage": "desktop-coarse-poc",
                "automaticApproval": False,
                "productionReady": False,
                "aaaQualityClaim": False,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    unreal.log(f"Gahyeon v024 assembly clean reload verified: assets={len(assembled_assets)}")


validate()
