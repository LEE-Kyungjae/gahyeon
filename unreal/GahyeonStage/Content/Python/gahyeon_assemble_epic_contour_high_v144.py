"""Assemble cloud-enriched v142 as an immutable GPU High MetaHuman."""

import json
from pathlib import Path

import unreal


CHARACTER = "/Game/Gahyeon/CharacterPipeline/v142/Character/MHC_Gahyeon_EpicContour_v142"
BUILD_ROOT = "/Game/Gahyeon/CharacterPipeline/v144/AssembledHigh"
COMMON_ROOT = "/Game/Gahyeon/CharacterPipeline/v144/CommonHigh"
NAME = "Gahyeon_EpicContourHigh_v144"
ENRICHMENT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v143-metahuman-epic-contour-cloud/enrichment-receipt.json"
)
RECEIPT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v144-metahuman-epic-contour-high/assembly-receipt.json"
)


def assemble_epic_contour_high_v144():
    if RECEIPT.exists():
        raise RuntimeError("refusing to overwrite immutable v144 receipt")
    if json.loads(ENRICHMENT.read_text(encoding="utf-8")).get("state") != "cloud-enriched-buildable-awaiting-assembly":
        raise RuntimeError("v143 lineage is not ready for High assembly")
    for root in (BUILD_ROOT, COMMON_ROOT):
        if unreal.EditorAssetLibrary.does_directory_exist(root):
            if unreal.EditorAssetLibrary.list_assets(root, recursive=True, include_folder=False):
                raise RuntimeError(f"refusing to overwrite v144 assets: {root}")
    character = unreal.load_asset(CHARACTER)
    if character is None or character.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError(f"v142 MetaHuman Character unavailable: {CHARACTER}")
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    if not subsystem.try_add_object_to_edit(character):
        raise RuntimeError("failed to initialize v142 for v144 High assembly")
    try:
        if not subsystem.can_build_meta_human(character, True):
            raise RuntimeError("v142 failed MetaHuman pre-assembly validation")
        params = unreal.MetaHumanCharacterEditorBuildParameters()
        params.pipeline_type = unreal.MetaHumanDefaultPipelineType.OPTIMIZED
        params.pipeline_quality = unreal.MetaHumanQualityLevel.HIGH
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
        raise RuntimeError(f"expected one v144 Blueprint, got {blueprints}")
    for root in (BUILD_ROOT, COMMON_ROOT):
        if not unreal.EditorAssetLibrary.save_directory(root, only_if_is_dirty=False, recursive=True):
            raise RuntimeError(f"failed to save v144 assembly: {root}")
    RECEIPT.parent.mkdir(parents=True, exist_ok=False)
    RECEIPT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v144",
        "state": "draft-high-epic-contour-assembly",
        "engine": "5.8",
        "sourceCharacter": CHARACTER,
        "enrichmentReceipt": str(ENRICHMENT),
        "assembledBlueprint": blueprints[0],
        "pipelineType": "OPTIMIZED",
        "pipelineQuality": "HIGH",
        "gpuRhiRequired": True,
        "assembledAssetCount": len(assets),
        "automaticApproval": False,
        "productionReady": False,
    }, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v144 GPU High assembly complete: {blueprints[0]}")
    unreal.SystemLibrary.quit_editor()


assemble_epic_contour_high_v144()
