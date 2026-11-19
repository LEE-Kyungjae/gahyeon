"""Assemble calibrated v120 as an immutable GPU High MetaHuman POC."""

import json
from pathlib import Path

import unreal


CHARACTER = "/Game/Gahyeon/CharacterPipeline/v120/Character/MHC_Gahyeon_LowerFace_v120"
BUILD_ROOT = "/Game/Gahyeon/CharacterPipeline/v122/AssembledHigh"
COMMON_ROOT = "/Game/Gahyeon/CharacterPipeline/v122/CommonHigh"
NAME = "Gahyeon_LowerFaceHigh_v122"
ENRICHMENT_RECEIPT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v121-metahuman-lower-face-cloud/enrichment-receipt.json"
)
RECEIPT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v122-metahuman-lower-face-high/assembly-receipt.json"
)


def assemble_lower_face_high_v122():
    if RECEIPT.exists():
        raise RuntimeError(f"refusing to overwrite immutable v122 receipt: {RECEIPT}")
    enrichment = json.loads(ENRICHMENT_RECEIPT.read_text(encoding="utf-8"))
    if enrichment.get("state") != "cloud-enriched-buildable-awaiting-assembly":
        raise RuntimeError("v121 cloud enrichment lineage is not ready for assembly")
    for root in (BUILD_ROOT, COMMON_ROOT):
        if unreal.EditorAssetLibrary.does_directory_exist(root):
            existing = unreal.EditorAssetLibrary.list_assets(root, recursive=True, include_folder=False)
            if existing:
                raise RuntimeError(f"refusing to overwrite v122 assets: {root}")
    character = unreal.load_asset(CHARACTER)
    if character is None or character.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError(f"v120 MetaHuman Character unavailable: {CHARACTER}")
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    if not subsystem.try_add_object_to_edit(character):
        raise RuntimeError("failed to initialize v120 for v122 High assembly")
    try:
        if not subsystem.can_build_meta_human(character, True):
            raise RuntimeError("v120 failed MetaHuman pre-assembly validation")
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
        raise RuntimeError(f"expected one v122 Blueprint, got {blueprints}")
    for root in (BUILD_ROOT, COMMON_ROOT):
        if not unreal.EditorAssetLibrary.save_directory(root, only_if_is_dirty=False, recursive=True):
            raise RuntimeError(f"failed to save v122 assembly: {root}")
    RECEIPT.parent.mkdir(parents=True, exist_ok=False)
    RECEIPT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v122",
        "state": "draft-high-qa-assembly",
        "engine": "5.8",
        "hypothesis": "The measured calibrated v120 native sculpt is large enough to be judged visually while preserving production MetaHuman topology and rigging.",
        "action": "Build the v121 cloud-enriched character through OPTIMIZED HIGH with a real GPU RHI.",
        "expectedResult": "One saved High-quality MetaHuman Blueprint suitable for fixed-camera comparison against v113.",
        "sourceCharacter": CHARACTER,
        "enrichmentReceipt": str(ENRICHMENT_RECEIPT),
        "assembledBlueprint": blueprints[0],
        "pipelineType": "OPTIMIZED",
        "pipelineQuality": "HIGH",
        "gpuRhiRequired": True,
        "wardrobeValidation": True,
        "assembledAssetCount": len(assets),
        "automaticApproval": False,
        "productionReady": False,
    }, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v122 GPU High assembly complete: {blueprints[0]}")
    unreal.SystemLibrary.quit_editor()


assemble_lower_face_high_v122()
