"""Assemble the retained v024 solved identity at Medium quality without overwrite."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import unreal


CHARACTER_PATH = "/Game/Gahyeon/CharacterPipeline/v024/Character/MHC_Gahyeon_CoarsePOC_v024"
BUILD_ROOT = "/Game/Gahyeon/CharacterPipeline/v057/AssembledMedium"
COMMON_ROOT = "/Game/Gahyeon/CharacterPipeline/v057/CommonMedium"
NAME_OVERRIDE = "Gahyeon_IdentityMedium_v057"


def assemble_identity_medium_v057():
    workspace = Path(os.environ.get("GAHYEON_WORKSPACE", "/Users/ze/work/gahyeonbot"))
    receipt_path = workspace / "artifacts/gahyeon-ch/metahuman-identity-medium-v057-assembly.json"
    if receipt_path.exists():
        raise RuntimeError(f"refusing to overwrite immutable receipt: {receipt_path}")
    for path in (BUILD_ROOT, COMMON_ROOT):
        if unreal.EditorAssetLibrary.does_directory_exist(path):
            existing = unreal.EditorAssetLibrary.list_assets(path, recursive=True, include_folder=False)
            if existing:
                raise RuntimeError(f"refusing to overwrite existing iteration assets: {path}")

    character = unreal.EditorAssetLibrary.load_asset(CHARACTER_PATH)
    if character is None or character.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError(f"MetaHuman Character is unavailable: {CHARACTER_PATH}")

    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    if not subsystem.try_add_object_to_edit(character):
        raise RuntimeError("failed to initialize v024 MetaHuman Character for assembly")
    try:
        if not subsystem.can_build_meta_human(character, True):
            raise RuntimeError("v024 MetaHuman Character failed the pre-assembly readiness check")
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

    assembled_assets = list(
        unreal.EditorAssetLibrary.list_assets(BUILD_ROOT, recursive=True, include_folder=False)
    )
    if not assembled_assets:
        raise RuntimeError("v057 Medium assembly returned without producing assets")
    for path in (BUILD_ROOT, COMMON_ROOT):
        if not unreal.EditorAssetLibrary.save_directory(path, only_if_is_dirty=False, recursive=True):
            raise RuntimeError(f"failed to save assembled MetaHuman assets: {path}")

    blueprint_assets = [path for path in assembled_assets if path.rsplit("/", 1)[-1].startswith("BP_")]
    if len(blueprint_assets) != 1:
        raise RuntimeError(f"expected exactly one assembled Blueprint, got: {blueprint_assets}")
    receipt = {
        "schemaVersion": 1,
        "observedAt": datetime.now(timezone.utc).isoformat(),
        "iteration": "v057",
        "engine": "Unreal Engine 5.8",
        "sourceCharacter": CHARACTER_PATH,
        "buildRoot": BUILD_ROOT,
        "commonRoot": COMMON_ROOT,
        "assembledBlueprint": blueprint_assets[0],
        "pipelineType": "OPTIMIZED",
        "pipelineQuality": "MEDIUM",
        "animationSystem": "AnimBP",
        "assembledAssetCount": len(assembled_assets),
        "assembledAssets": assembled_assets,
        "hypothesis": "Medium assembly separates low-LOD packaging defects from v024 identity-solve defects.",
        "status": "draft",
        "automaticApproval": False,
        "productionReady": False,
        "aaaQualityClaim": False,
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v057 Medium identity assembly complete: {json.dumps(receipt)}")


assemble_identity_medium_v057()
