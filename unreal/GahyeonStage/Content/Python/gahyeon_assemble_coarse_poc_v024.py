"""Assemble the enriched v024 MetaHuman as a desktop-oriented optimized POC."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import unreal


CHARACTER_PATH = "/Game/Gahyeon/CharacterPipeline/v026/Character/MHC_Skotukeda_Baseline_v026"
BUILD_ROOT = "/Game/Gahyeon/CharacterPipeline/v027/AssembledMedium"
COMMON_ROOT = "/Game/Gahyeon/CharacterPipeline/v027/CommonMedium"
NAME_OVERRIDE = "Skotukeda_Medium_v027"


def assemble():
    workspace = Path(os.environ.get("GAHYEON_WORKSPACE", "/Users/ze/work/gahyeonbot"))
    receipt_path = workspace / "artifacts/gahyeon-ch/metahuman-template-medium-v027-assembly.json"
    if receipt_path.exists():
        raise RuntimeError(f"refusing to overwrite immutable assembly receipt: {receipt_path}")
    if unreal.EditorAssetLibrary.does_directory_exist(BUILD_ROOT):
        existing = unreal.EditorAssetLibrary.list_assets(BUILD_ROOT, recursive=True, include_folder=False)
        if existing:
            raise RuntimeError(f"refusing to overwrite existing assembled iteration: {BUILD_ROOT}")

    character = unreal.EditorAssetLibrary.load_asset(CHARACTER_PATH)
    if character is None:
        raise RuntimeError(f"MetaHuman Character is unavailable: {CHARACTER_PATH}")
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    if not subsystem.try_add_object_to_edit(character):
        raise RuntimeError("failed to initialize MetaHuman Character for assembly")
    try:
        if not subsystem.can_build_meta_human(character, True):
            raise RuntimeError("MetaHuman Character failed the pre-assembly readiness check")
        params = unreal.MetaHumanCharacterEditorBuildParameters()
        params.pipeline_type = unreal.MetaHumanDefaultPipelineType.OPTIMIZED
        params.pipeline_quality = unreal.MetaHumanQualityLevel.MEDIUM
        params.animation_system_name = "AnimBP"
        params.absolute_build_path = BUILD_ROOT
        params.common_folder_path = COMMON_ROOT
        params.name_override = NAME_OVERRIDE
        subsystem.build_meta_human(character, params)
    finally:
        subsystem.remove_object_to_edit(character)

    assembled_assets = list(unreal.EditorAssetLibrary.list_assets(
        BUILD_ROOT, recursive=True, include_folder=False
    ))
    if not assembled_assets:
        raise RuntimeError("MetaHuman assembly returned without producing assets")
    if not unreal.EditorAssetLibrary.save_directory(
        BUILD_ROOT, only_if_is_dirty=False, recursive=True
    ):
        raise RuntimeError(f"failed to save assembled MetaHuman assets: {BUILD_ROOT}")
    if not unreal.EditorAssetLibrary.save_directory(
        COMMON_ROOT, only_if_is_dirty=False, recursive=True
    ):
        raise RuntimeError(f"failed to save assembled MetaHuman common assets: {COMMON_ROOT}")

    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "observedAt": datetime.now(timezone.utc).isoformat(),
                "iteration": "v027",
                "engine": "Unreal Engine 5.8",
                "characterAsset": CHARACTER_PATH,
                "buildRoot": BUILD_ROOT,
                "commonRoot": COMMON_ROOT,
                "pipelineType": "OPTIMIZED",
                "pipelineQuality": "MEDIUM",
                "animationSystem": "AnimBP",
                "assembledAssetCount": len(assembled_assets),
                "assembledAssets": assembled_assets,
                "qualityStage": "desktop-medium-material-poc",
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
    unreal.log(f"Gahyeon v027 medium template assembly complete: assets={len(assembled_assets)}")


assemble()
