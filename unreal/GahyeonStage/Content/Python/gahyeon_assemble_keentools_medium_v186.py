"""Assemble cloud-enriched KeenTools v183 as an immutable GPU Medium MetaHuman."""

import json
from pathlib import Path

import unreal


CHARACTER = "/Game/Gahyeon/CharacterPipeline/v183/Character/MHC_Gahyeon_KeenTools_v183"
BUILD_ROOT = "/Game/Gahyeon/CharacterPipeline/v186/AssembledMedium"
COMMON_ROOT = "/Game/Gahyeon/CharacterPipeline/v186/CommonMedium"
NAME = "Gahyeon_KeenToolsMedium_v186"
ENRICHMENT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v185-metahuman-keentools-cloud/enrichment-receipt.json"
)
RECEIPT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v186-metahuman-keentools-medium/assembly-receipt.json"
)


def assemble_keentools_medium_v186():
    if RECEIPT.exists():
        raise RuntimeError("refusing to overwrite immutable v186 receipt")
    if json.loads(ENRICHMENT.read_text(encoding="utf-8")).get("state") != "cloud-enriched-buildable-awaiting-assembly":
        raise RuntimeError("v185 lineage is not ready for Medium assembly")
    for root in (BUILD_ROOT, COMMON_ROOT):
        if unreal.EditorAssetLibrary.does_directory_exist(root):
            if unreal.EditorAssetLibrary.list_assets(root, recursive=True, include_folder=False):
                raise RuntimeError(f"refusing to overwrite v186 assets: {root}")
    character = unreal.load_asset(CHARACTER)
    if character is None or character.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError(f"v183 MetaHuman Character unavailable: {CHARACTER}")
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    if not subsystem.try_add_object_to_edit(character):
        raise RuntimeError("failed to initialize v183 for v186 Medium assembly")
    try:
        if not subsystem.can_build_meta_human(character, True):
            raise RuntimeError("v183 failed MetaHuman pre-assembly validation")
        params = unreal.MetaHumanCharacterEditorBuildParameters()
        params.pipeline_type = unreal.MetaHumanDefaultPipelineType.OPTIMIZED
        params.pipeline_quality = unreal.MetaHumanQualityLevel.MEDIUM
        params.animation_system_name = "AnimBP"
        params.absolute_build_path = BUILD_ROOT
        params.common_folder_path = COMMON_ROOT
        params.name_override = NAME
        params.enable_wardrobe_item_validation = True
        subsystem.build_meta_human(character, params)
    finally:
        if subsystem.is_object_added_for_editing(character):
            subsystem.remove_object_to_edit(character)
    assets = list(unreal.EditorAssetLibrary.list_assets(BUILD_ROOT, recursive=True, include_folder=False))
    blueprints = [path for path in assets if path.rsplit("/", 1)[-1].startswith("BP_")]
    if len(blueprints) != 1:
        raise RuntimeError(f"expected one v186 Blueprint, got {blueprints}")
    for root in (BUILD_ROOT, COMMON_ROOT):
        if not unreal.EditorAssetLibrary.save_directory(root, only_if_is_dirty=False, recursive=True):
            raise RuntimeError(f"failed to save v186 assembly: {root}")
    RECEIPT.parent.mkdir(parents=True, exist_ok=False)
    RECEIPT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v186",
        "state": "draft-medium-keentools-assembly-awaiting-fixed-camera-qa",
        "engine": "5.8",
        "sourceCharacter": CHARACTER,
        "enrichmentReceipt": str(ENRICHMENT),
        "assembledBlueprint": blueprints[0],
        "pipelineType": "OPTIMIZED",
        "pipelineQuality": "MEDIUM",
        "gpuRhiRequired": True,
        "assembledAssetCount": len(assets),
        "automaticApproval": False,
        "productionReady": False,
    }, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v186 GPU Medium assembly complete: {blueprints[0]}")
    unreal.SystemLibrary.quit_editor()


assemble_keentools_medium_v186()
