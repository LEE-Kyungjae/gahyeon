"""Retry v109b High assembly with a GPU RHI after the immutable v111 NullRHI crash."""

import json
from pathlib import Path

import unreal


CHARACTER = "/Game/Gahyeon/CharacterPipeline/v109b/Character/MHC_Gahyeon_LowerFace_v109b"
BUILD_ROOT = "/Game/Gahyeon/CharacterPipeline/v111b/AssembledHigh"
COMMON_ROOT = "/Game/Gahyeon/CharacterPipeline/v111b/CommonHigh"
NAME = "Gahyeon_LowerFaceHigh_v111b"
ENRICHMENT_RECEIPT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v110b-metahuman-lower-face-cloud/enrichment-receipt.json"
)
FAILURE_RECEIPT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v111-metahuman-lower-face-high/failure-receipt.json"
)
RECEIPT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v111b-metahuman-lower-face-high-gpu/assembly-receipt.json"
)


def assemble_lower_face_high_v111b():
    if RECEIPT.exists():
        raise RuntimeError(f"refusing to overwrite immutable v111b receipt: {RECEIPT}")
    if not ENRICHMENT_RECEIPT.is_file() or not FAILURE_RECEIPT.is_file():
        raise RuntimeError("v110b enrichment or v111 failure lineage is unavailable")
    enrichment = json.loads(ENRICHMENT_RECEIPT.read_text(encoding="utf-8"))
    failure = json.loads(FAILURE_RECEIPT.read_text(encoding="utf-8"))
    if enrichment.get("state") != "cloud-enriched-buildable-awaiting-assembly":
        raise RuntimeError("v110b cloud enrichment lineage is not ready for assembly")
    if failure.get("decision") != "reject-and-retry-with-gpu-rhi-in-v111b":
        raise RuntimeError("v111 failure does not authorize the GPU-RHI retry")
    for root in (BUILD_ROOT, COMMON_ROOT):
        if unreal.EditorAssetLibrary.does_directory_exist(root):
            existing = unreal.EditorAssetLibrary.list_assets(root, recursive=True, include_folder=False)
            if existing:
                raise RuntimeError(f"refusing to overwrite v111b assets: {root}")

    character = unreal.load_asset(CHARACTER)
    if character is None or character.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError(f"v109b MetaHuman Character unavailable: {CHARACTER}")
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    if not subsystem.try_add_object_to_edit(character):
        raise RuntimeError("failed to initialize v109b for v111b High assembly")
    try:
        if not subsystem.can_build_meta_human(character, True):
            raise RuntimeError("v109b failed MetaHuman pre-assembly validation")
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
        raise RuntimeError(f"expected one v111b Blueprint, got {blueprints}")
    for root in (BUILD_ROOT, COMMON_ROOT):
        if not unreal.EditorAssetLibrary.save_directory(root, only_if_is_dirty=False, recursive=True):
            raise RuntimeError(f"failed to save v111b assembly: {root}")

    RECEIPT.parent.mkdir(parents=True, exist_ok=False)
    RECEIPT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v111b",
        "state": "draft-high-qa-assembly",
        "engine": "5.8",
        "hypothesis": "The v111 native crash was caused by NullRHI being incompatible with TextureGraph wardrobe and groom material baking, not by the sculpted MetaHuman data.",
        "action": "Rebuild the identical cloud-enriched v109b character through OPTIMIZED HIGH with a real GPU RHI.",
        "expectedResult": "TextureGraph material baking completes and produces one saved High-quality MetaHuman Blueprint.",
        "sourceCharacter": CHARACTER,
        "enrichmentReceipt": str(ENRICHMENT_RECEIPT),
        "failedPredecessorReceipt": str(FAILURE_RECEIPT),
        "assembledBlueprint": blueprints[0],
        "pipelineType": "OPTIMIZED",
        "pipelineQuality": "HIGH",
        "gpuRhiRequired": True,
        "wardrobeValidation": True,
        "assembledAssetCount": len(assets),
        "automaticApproval": False,
        "productionReady": False,
    }, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v111b GPU High assembly complete: {blueprints[0]}")
    unreal.SystemLibrary.quit_editor()


assemble_lower_face_high_v111b()
