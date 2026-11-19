"""Assemble cloud-enriched v167 as an immutable GPU Medium MetaHuman."""

import json
from pathlib import Path

import unreal


CHARACTER = "/Game/Gahyeon/CharacterPipeline/v167/Character/MHC_Gahyeon_FaceBuilder_v167"
BUILD_ROOT = "/Game/Gahyeon/CharacterPipeline/v169/AssembledMedium"
COMMON_ROOT = "/Game/Gahyeon/CharacterPipeline/v169/CommonMedium"
NAME = "Gahyeon_FaceBuilderMedium_v169"
ENRICHMENT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v168-metahuman-facebuilder-cloud/enrichment-receipt.json"
)
RECEIPT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v169-metahuman-facebuilder-medium/assembly-receipt.json"
)


def assemble_facebuilder_medium_v169():
    if RECEIPT.exists():
        raise RuntimeError("refusing to overwrite immutable v169 receipt")
    if json.loads(ENRICHMENT.read_text(encoding="utf-8")).get("state") != "cloud-enriched-buildable-awaiting-assembly":
        raise RuntimeError("v168 lineage is not ready for Medium assembly")
    for root in (BUILD_ROOT, COMMON_ROOT):
        if unreal.EditorAssetLibrary.does_directory_exist(root):
            if unreal.EditorAssetLibrary.list_assets(root, recursive=True, include_folder=False):
                raise RuntimeError(f"refusing to overwrite v169 assets: {root}")
    character = unreal.load_asset(CHARACTER)
    if character is None or character.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError(f"v167 MetaHuman Character unavailable: {CHARACTER}")
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    if not subsystem.try_add_object_to_edit(character):
        raise RuntimeError("failed to initialize v167 for v169 Medium assembly")
    try:
        if not subsystem.can_build_meta_human(character, True):
            raise RuntimeError("v167 failed MetaHuman pre-assembly validation")
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
        raise RuntimeError(f"expected one v169 Blueprint, got {blueprints}")
    for root in (BUILD_ROOT, COMMON_ROOT):
        if not unreal.EditorAssetLibrary.save_directory(root, only_if_is_dirty=False, recursive=True):
            raise RuntimeError(f"failed to save v169 assembly: {root}")
    RECEIPT.parent.mkdir(parents=True, exist_ok=False)
    RECEIPT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v169",
        "state": "draft-medium-facebuilder-assembly-awaiting-fixed-camera-qa",
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
    unreal.log(f"Gahyeon v169 GPU Medium assembly complete: {blueprints[0]}")
    unreal.SystemLibrary.quit_editor()


assemble_facebuilder_medium_v169()
