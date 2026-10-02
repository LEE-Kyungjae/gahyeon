"""Assemble the immutable Fab Skotukeda source directly at High quality."""

import json
from pathlib import Path

import unreal


SOURCE = "/Game/Fab/MetaHuman/Skotukeda"
BUILD_ROOT = "/Game/Gahyeon/CharacterPipeline/v237/AssembledHigh"
COMMON_ROOT = "/Game/Gahyeon/CharacterPipeline/v237/CommonHigh"
NAME = "Skotukeda_GoldenHigh_v237"
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v237-skotukeda-golden-high/assembly-report.json"
)


def assemble_golden_skotukeda_high_v237():
    if REPORT.exists():
        raise RuntimeError("refusing to overwrite immutable v237 report")
    for root in (BUILD_ROOT, COMMON_ROOT):
        if unreal.EditorAssetLibrary.does_directory_exist(root):
            assets = unreal.EditorAssetLibrary.list_assets(root, recursive=True, include_folder=False)
            if assets:
                raise RuntimeError(f"refusing to overwrite v237 assets: {root}")

    character = unreal.load_asset(SOURCE)
    if character is None or character.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError(f"immutable Fab MetaHuman source unavailable: {SOURCE}")
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    if not subsystem.try_add_object_to_edit(character):
        raise RuntimeError("failed to initialize immutable source for High assembly")
    try:
        if not subsystem.can_build_meta_human(character, True):
            raise RuntimeError("immutable source failed MetaHuman pre-assembly validation")
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
    blueprints = [asset for asset in assets if asset.rsplit("/", 1)[-1].startswith("BP_")]
    if len(blueprints) != 1:
        raise RuntimeError(f"expected exactly one v237 Blueprint, got: {blueprints}")
    for root in (BUILD_ROOT, COMMON_ROOT):
        if not unreal.EditorAssetLibrary.save_directory(root, only_if_is_dirty=False, recursive=True):
            raise RuntimeError(f"failed to save v237 assembly: {root}")

    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v237",
        "state": "built-draft-golden-high-assembly",
        "sourceCharacter": SOURCE,
        "sourceModified": False,
        "assembledBlueprint": blueprints[0],
        "pipelineType": "OPTIMIZED",
        "pipelineQuality": "HIGH",
        "animationSystem": "AnimBP",
        "textureSourceMode": "preserve-existing-local-source",
        "wardrobeValidation": True,
        "assembledAssetCount": len(assets),
        "automaticApproval": False,
        "productionReady": False,
    }, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v237 golden High assembly complete: {blueprints[0]}")
    unreal.SystemLibrary.quit_editor()


assemble_golden_skotukeda_high_v237()
