"""Assemble enriched Stella v661 as an immutable GPU Medium MetaHuman."""

import json
from pathlib import Path

import unreal


CHARACTER = "/Game/LivingCharacterPOC/v661/Character/MHC_StellaLily_Draft_v661"
BUILD_ROOT = "/Game/LivingCharacterPOC/v664/AssembledMedium"
COMMON_ROOT = "/Game/LivingCharacterPOC/v664/CommonMedium"
NAME = "StellaLily_MetaHumanMedium_v664"
ENRICHMENT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/"
    "living-character-poc-v663-stella-metahuman-enrichment/enrichment-receipt.json"
)
RECEIPT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/"
    "living-character-poc-v664-stella-metahuman-assembly/assembly-receipt.json"
)


def assemble_stella_metahuman_v664():
    if RECEIPT.exists():
        raise RuntimeError("refusing to overwrite immutable v664 receipt")
    enrichment = json.loads(ENRICHMENT.read_text(encoding="utf-8"))
    if enrichment.get("state") != "enriched-buildable-awaiting-assembly":
        raise RuntimeError("Stella v663 enrichment lineage is not ready")
    for root in (BUILD_ROOT, COMMON_ROOT):
        if unreal.EditorAssetLibrary.list_assets(root, recursive=True, include_folder=False):
            raise RuntimeError(f"refusing to overwrite v664 assets: {root}")
    character = unreal.load_asset(CHARACTER)
    if character is None or character.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError(f"Stella v661 MetaHuman unavailable: {CHARACTER}")
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    if not subsystem.try_add_object_to_edit(character):
        raise RuntimeError("failed to initialize Stella for v664 assembly")
    try:
        if not subsystem.can_build_meta_human(character, True):
            raise RuntimeError("Stella failed MetaHuman pre-assembly validation")
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
    assets = list(
        unreal.EditorAssetLibrary.list_assets(BUILD_ROOT, recursive=True, include_folder=False)
    )
    blueprints = [path for path in assets if path.rsplit("/", 1)[-1].startswith("BP_")]
    if len(blueprints) != 1:
        raise RuntimeError(f"expected one Stella v664 Blueprint, got {blueprints}")
    for root in (BUILD_ROOT, COMMON_ROOT):
        if not unreal.EditorAssetLibrary.save_directory(
            root, only_if_is_dirty=False, recursive=True
        ):
            raise RuntimeError(f"failed to save Stella v664 assembly: {root}")
    RECEIPT.parent.mkdir(parents=True, exist_ok=False)
    RECEIPT.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "iteration": "v664",
                "state": "draft-medium-assembly-awaiting-fixed-camera-qa",
                "engine": "5.8",
                "sourceCharacter": CHARACTER,
                "enrichmentReceipt": str(ENRICHMENT),
                "assembledBlueprint": blueprints[0],
                "pipelineType": "OPTIMIZED",
                "pipelineQuality": "MEDIUM",
                "assembledAssetCount": len(assets),
                "automaticApproval": False,
                "productionReady": False,
            },
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    unreal.log(f"Stella v664 assembly complete: {blueprints[0]}")
    unreal.SystemLibrary.quit_editor()


assemble_stella_metahuman_v664()
