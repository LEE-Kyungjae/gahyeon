"""Resume v058 after conform: obtain required cloud assets and assemble Medium."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import unreal


CHARACTER = "/Game/Gahyeon/CharacterPipeline/v058/Character/MHC_Gahyeon_DefaultOral_v058"
BUILD_ROOT = "/Game/Gahyeon/CharacterPipeline/v058/AssembledMedium"
COMMON_ROOT = "/Game/Gahyeon/CharacterPipeline/v058/CommonMedium"
NAME_OVERRIDE = "Gahyeon_DefaultOral_v058"


def enrich_and_assemble_default_oral_v058():
    workspace = Path(os.environ.get("GAHYEON_WORKSPACE", "/Users/ze/work/gahyeonbot"))
    conform_receipt = workspace / "artifacts/gahyeon-ch/metahuman-default-oral-v058-conform.json"
    enrichment_receipt = workspace / "artifacts/gahyeon-ch/metahuman-default-oral-v058-enrichment.json"
    assembly_receipt = workspace / "artifacts/gahyeon-ch/metahuman-default-oral-v058-assembly.json"
    if not conform_receipt.is_file():
        raise RuntimeError(f"v058 conform receipt missing: {conform_receipt}")
    for receipt in (enrichment_receipt, assembly_receipt):
        if receipt.exists():
            raise RuntimeError(f"refusing to overwrite immutable receipt: {receipt}")
    for path in (BUILD_ROOT, COMMON_ROOT):
        existing = unreal.EditorAssetLibrary.list_assets(path, recursive=True, include_folder=False)
        if existing:
            raise RuntimeError(f"refusing to overwrite existing iteration assets: {path}")

    character = unreal.EditorAssetLibrary.load_asset(CHARACTER)
    if character is None or character.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError(f"v058 MetaHuman Character missing: {CHARACTER}")
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    if not subsystem.try_add_object_to_edit(character):
        raise RuntimeError("v058 MetaHuman Character is unavailable for enrichment")
    try:
        rig = unreal.MetaHumanCharacterAutoRiggingRequestParams()
        rig.blocking = True
        rig.report_progress = False
        rig.rig_type = unreal.MetaHumanRigType.JOINTS_AND_BLEND_SHAPES
        subsystem.request_auto_rigging(character, rig)
        textures = unreal.MetaHumanCharacterTextureRequestParams()
        textures.blocking = True
        textures.report_progress = False
        subsystem.request_texture_sources(character, textures)
        if not unreal.EditorAssetLibrary.save_loaded_asset(character, only_if_is_dirty=False):
            raise RuntimeError(f"failed to save enriched character: {CHARACTER}")
        if not subsystem.can_build_meta_human(character, True):
            raise RuntimeError("v058 remains unbuildable after cloud enrichment")

        enrichment = {
            "schemaVersion": 1,
            "observedAt": datetime.now(timezone.utc).isoformat(),
            "iteration": "v058",
            "characterAsset": CHARACTER,
            "textureSourcesRequested": True,
            "autoRigRequested": True,
            "rigType": "JOINTS_AND_BLENDSHAPES",
            "canAssemble": True,
            "status": "draft",
            "automaticApproval": False,
            "productionReady": False,
            "aaaQualityClaim": False,
        }
        enrichment_receipt.parent.mkdir(parents=True, exist_ok=True)
        enrichment_receipt.write_text(
            json.dumps(enrichment, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

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
        "sourceCharacter": CHARACTER,
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
    assembly_receipt.write_text(
        json.dumps(assembly, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    unreal.log(f"Gahyeon v058 default-eye/teeth Medium assembly complete: {json.dumps(assembly)}")


enrich_and_assemble_default_oral_v058()
