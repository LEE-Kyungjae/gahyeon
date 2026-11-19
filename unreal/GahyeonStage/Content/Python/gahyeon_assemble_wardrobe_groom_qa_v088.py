"""Assemble v087 into an isolated Medium QA Blueprint for render validation."""

import json
from pathlib import Path

import unreal


CHARACTER = "/Game/Gahyeon/CharacterPipeline/v087/Character/MHC_Skotukeda_WardrobeGroom_v087"
BUILD_ROOT = "/Game/Gahyeon/CharacterPipeline/v088/AssembledMedium"
COMMON_ROOT = "/Game/Gahyeon/CharacterPipeline/v088/CommonMedium"
NAME = "Skotukeda_WardrobeGroomQA_v088"
RECEIPT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v088-wardrobe-groom-qa/assembly-receipt.json"
)


def assemble():
    if RECEIPT.exists():
        raise RuntimeError("refusing to overwrite immutable v088 receipt")
    for root in (BUILD_ROOT, COMMON_ROOT):
        if unreal.EditorAssetLibrary.does_directory_exist(root):
            if unreal.EditorAssetLibrary.list_assets(root, recursive=True, include_folder=False):
                raise RuntimeError(f"refusing to overwrite v088 assets: {root}")

    character = unreal.load_asset(CHARACTER)
    if character is None or character.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError(f"v087 MetaHuman Character unavailable: {CHARACTER}")
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    if not subsystem.try_add_object_to_edit(character):
        raise RuntimeError("failed to initialize v087 for QA assembly")
    try:
        textures = unreal.MetaHumanCharacterTextureRequestParams()
        textures.blocking = True
        textures.report_progress = False
        subsystem.request_texture_sources(character, textures)
        if not unreal.EditorAssetLibrary.save_loaded_asset(character, only_if_is_dirty=False):
            raise RuntimeError("failed to save v087 texture sources")
        if not subsystem.can_build_meta_human(character, True):
            raise RuntimeError("v087 failed MetaHuman pre-assembly validation")
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
        raise RuntimeError(f"expected one v088 Blueprint, got {blueprints}")
    for root in (BUILD_ROOT, COMMON_ROOT):
        if not unreal.EditorAssetLibrary.save_directory(root, only_if_is_dirty=False, recursive=True):
            raise RuntimeError(f"failed to save v088 assembly: {root}")

    RECEIPT.parent.mkdir(parents=True, exist_ok=False)
    RECEIPT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v088",
        "state": "draft-medium-qa-assembly",
        "sourceCharacter": CHARACTER,
        "assembledBlueprint": blueprints[0],
        "pipelineType": "OPTIMIZED",
        "pipelineQuality": "MEDIUM",
        "textureSourcesRequested": True,
        "wardrobeValidation": True,
        "assembledAssetCount": len(assets),
        "automaticApproval": False,
        "productionReady": False,
    }, indent=2) + "\n")
    unreal.log(f"Gahyeon v088 QA assembly complete: {blueprints[0]}")


assemble()
