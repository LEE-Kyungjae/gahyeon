"""Assemble the cloud-enriched v109b MetaHuman at High quality for fixed-camera QA."""

import json
from pathlib import Path

import unreal


CHARACTER = "/Game/Gahyeon/CharacterPipeline/v109b/Character/MHC_Gahyeon_LowerFace_v109b"
BUILD_ROOT = "/Game/Gahyeon/CharacterPipeline/v111/AssembledHigh"
COMMON_ROOT = "/Game/Gahyeon/CharacterPipeline/v111/CommonHigh"
NAME = "Gahyeon_LowerFaceHigh_v111"
ENRICHMENT_RECEIPT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v110b-metahuman-lower-face-cloud/enrichment-receipt.json"
)
RECEIPT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v111-metahuman-lower-face-high/assembly-receipt.json"
)


def assemble_lower_face_high_v111():
    if RECEIPT.exists():
        raise RuntimeError(f"refusing to overwrite immutable v111 receipt: {RECEIPT}")
    if not ENRICHMENT_RECEIPT.is_file():
        raise RuntimeError(f"v110b enrichment receipt unavailable: {ENRICHMENT_RECEIPT}")
    enrichment = json.loads(ENRICHMENT_RECEIPT.read_text(encoding="utf-8"))
    if enrichment.get("state") != "cloud-enriched-buildable-awaiting-assembly":
        raise RuntimeError("v110b cloud enrichment lineage is not ready for assembly")
    for root in (BUILD_ROOT, COMMON_ROOT):
        if unreal.EditorAssetLibrary.does_directory_exist(root):
            existing = unreal.EditorAssetLibrary.list_assets(root, recursive=True, include_folder=False)
            if existing:
                raise RuntimeError(f"refusing to overwrite v111 assets: {root}")

    character = unreal.load_asset(CHARACTER)
    if character is None or character.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError(f"v109b MetaHuman Character unavailable: {CHARACTER}")
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    if not subsystem.try_add_object_to_edit(character):
        raise RuntimeError("failed to initialize v109b for High assembly")
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
        raise RuntimeError(f"expected one v111 Blueprint, got {blueprints}")
    for root in (BUILD_ROOT, COMMON_ROOT):
        if not unreal.EditorAssetLibrary.save_directory(root, only_if_is_dirty=False, recursive=True):
            raise RuntimeError(f"failed to save v111 assembly: {root}")

    RECEIPT.parent.mkdir(parents=True, exist_ok=False)
    RECEIPT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v111",
        "state": "draft-high-qa-assembly",
        "engine": "5.8",
        "hypothesis": "A constrained native MetaHuman chin and lower-jaw lift reduces the excessive lower-face length without regressing facial widths or deformation topology.",
        "action": "Build cloud-enriched v109b with the official OPTIMIZED HIGH MetaHuman pipeline.",
        "expectedResult": "A rigged High-quality assembly suitable for fixed-camera comparison against v106 and the canonical references.",
        "sourceCharacter": CHARACTER,
        "enrichmentReceipt": str(ENRICHMENT_RECEIPT),
        "assembledBlueprint": blueprints[0],
        "pipelineType": "OPTIMIZED",
        "pipelineQuality": "HIGH",
        "wardrobeValidation": True,
        "assembledAssetCount": len(assets),
        "automaticApproval": False,
        "productionReady": False,
    }, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v111 High assembly complete: {blueprints[0]}")
    unreal.SystemLibrary.quit_editor()


assemble_lower_face_high_v111()
