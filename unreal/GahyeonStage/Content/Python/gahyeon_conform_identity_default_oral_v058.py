"""Conform v024 identity while retaining production MetaHuman eyes and teeth."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import unreal


SOURCE_CHARACTER = "/Game/Fab/MetaHuman/Skotukeda"
IDENTITY_ASSET = "/Game/Gahyeon/CharacterPipeline/v024/Identity/MHI_Gahyeon_v024"
TARGET_CHARACTER = "/Game/Gahyeon/CharacterPipeline/v058/Character/MHC_Gahyeon_DefaultOral_v058"
BUILD_ROOT = "/Game/Gahyeon/CharacterPipeline/v058/AssembledMedium"
COMMON_ROOT = "/Game/Gahyeon/CharacterPipeline/v058/CommonMedium"
NAME_OVERRIDE = "Gahyeon_DefaultOral_v058"


def conform_identity_default_oral_v058():
    workspace = Path(os.environ.get("GAHYEON_WORKSPACE", "/Users/ze/work/gahyeonbot"))
    conform_receipt = workspace / "artifacts/gahyeon-ch/metahuman-default-oral-v058-conform.json"
    assembly_receipt = workspace / "artifacts/gahyeon-ch/metahuman-default-oral-v058-assembly.json"
    for receipt in (conform_receipt, assembly_receipt):
        if receipt.exists():
            raise RuntimeError(f"refusing to overwrite immutable receipt: {receipt}")
    if unreal.EditorAssetLibrary.does_asset_exist(TARGET_CHARACTER):
        raise RuntimeError(f"refusing to overwrite existing target: {TARGET_CHARACTER}")
    for path in (BUILD_ROOT, COMMON_ROOT):
        if unreal.EditorAssetLibrary.does_directory_exist(path):
            existing = unreal.EditorAssetLibrary.list_assets(path, recursive=True, include_folder=False)
            if existing:
                raise RuntimeError(f"refusing to overwrite existing iteration assets: {path}")

    identity = unreal.EditorAssetLibrary.load_asset(IDENTITY_ASSET)
    source = unreal.EditorAssetLibrary.load_asset(SOURCE_CHARACTER)
    if identity is None or identity.get_class().get_name() != "MetaHumanIdentity":
        raise RuntimeError(f"solved MetaHuman Identity missing: {IDENTITY_ASSET}")
    if source is None or source.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError(f"source MetaHuman Character missing: {SOURCE_CHARACTER}")
    character = unreal.EditorAssetLibrary.duplicate_asset(SOURCE_CHARACTER, TARGET_CHARACTER)
    if character is None or character.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError(f"failed to duplicate source MetaHuman: {SOURCE_CHARACTER}")

    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    if not subsystem.try_add_object_to_edit(character):
        raise RuntimeError("v058 MetaHuman Character is unavailable for editing")
    try:
        params = unreal.ImportFromIdentityParams()
        params.use_eye_meshes = False
        params.use_teeth_mesh = False
        params.use_metric_scale = True
        result = subsystem.import_from_identity(character, identity, params)
        if result != unreal.ImportErrorCode.SUCCESS:
            raise RuntimeError(f"import_from_identity failed: {result}")
        subsystem.commit_face_state(character)
        if not unreal.EditorAssetLibrary.save_loaded_asset(character, only_if_is_dirty=False):
            raise RuntimeError(f"failed to save conformed character: {TARGET_CHARACTER}")
    finally:
        subsystem.remove_object_to_edit(character)

    conform = {
        "schemaVersion": 1,
        "observedAt": datetime.now(timezone.utc).isoformat(),
        "iteration": "v058",
        "sourceCharacter": SOURCE_CHARACTER,
        "identityAsset": IDENTITY_ASSET,
        "targetCharacter": TARGET_CHARACTER,
        "params": {"useEyeMeshes": False, "useTeethMesh": False, "useMetricScale": True},
        "hypothesis": "MetaHuman default eyes and teeth remove v024's giant detached ocular and oral geometry.",
        "result": "SUCCESS",
        "status": "draft",
        "automaticApproval": False,
        "identityApproved": False,
        "productionReady": False,
        "aaaQualityClaim": False,
    }
    conform_receipt.parent.mkdir(parents=True, exist_ok=True)
    conform_receipt.write_text(json.dumps(conform, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not subsystem.try_add_object_to_edit(character):
        raise RuntimeError("failed to reopen v058 MetaHuman Character for Medium assembly")
    try:
        if not subsystem.can_build_meta_human(character, True):
            raise RuntimeError("v058 MetaHuman Character failed the pre-assembly readiness check")
        build = unreal.MetaHumanCharacterEditorBuildParameters()
        build.pipeline_type = unreal.MetaHumanDefaultPipelineType.OPTIMIZED
        build.pipeline_quality = unreal.MetaHumanQualityLevel.MEDIUM
        build.animation_system_name = "AnimBP"
        build.absolute_build_path = BUILD_ROOT
        build.common_folder_path = COMMON_ROOT
        build.name_override = NAME_OVERRIDE
        subsystem.build_meta_human(character, build)
    finally:
        subsystem.remove_object_to_edit(character)

    assembled_assets = list(
        unreal.EditorAssetLibrary.list_assets(BUILD_ROOT, recursive=True, include_folder=False)
    )
    if not assembled_assets:
        raise RuntimeError("v058 Medium assembly returned without producing assets")
    for path in (BUILD_ROOT, COMMON_ROOT):
        if not unreal.EditorAssetLibrary.save_directory(path, only_if_is_dirty=False, recursive=True):
            raise RuntimeError(f"failed to save v058 assets: {path}")
    blueprints = [path for path in assembled_assets if path.rsplit("/", 1)[-1].startswith("BP_")]
    if len(blueprints) != 1:
        raise RuntimeError(f"expected exactly one v058 Blueprint, got: {blueprints}")
    assembly = {
        "schemaVersion": 1,
        "observedAt": datetime.now(timezone.utc).isoformat(),
        "iteration": "v058",
        "sourceCharacter": TARGET_CHARACTER,
        "buildRoot": BUILD_ROOT,
        "commonRoot": COMMON_ROOT,
        "assembledBlueprint": blueprints[0],
        "pipelineType": "OPTIMIZED",
        "pipelineQuality": "MEDIUM",
        "assembledAssetCount": len(assembled_assets),
        "assembledAssets": assembled_assets,
        "status": "draft",
        "automaticApproval": False,
        "productionReady": False,
        "aaaQualityClaim": False,
    }
    assembly_receipt.write_text(json.dumps(assembly, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v058 default-eye/teeth Medium assembly complete: {json.dumps(assembly)}")


conform_identity_default_oral_v058()
