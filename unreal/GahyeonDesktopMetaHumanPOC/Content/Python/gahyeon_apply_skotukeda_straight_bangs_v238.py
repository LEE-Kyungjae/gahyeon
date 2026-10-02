"""Apply the official long straight-bangs wardrobe item to a Skotukeda copy."""

import json
from pathlib import Path

import unreal


SOURCE = "/Game/Fab/MetaHuman/Skotukeda"
TARGET = "/Game/Gahyeon/CharacterPipeline/v238/Character/MHC_Skotukeda_StraightBangs_v238"
HAIR = (
    "/MetaHumanCharacter/Optional/Grooms/Bindings/Hair/"
    "WI_Hair_L_StraightBangs.WI_Hair_L_StraightBangs"
)
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v238-skotukeda-straight-bangs/build-report.json"
)


def _require(path, class_name):
    asset = unreal.load_asset(path)
    if asset is None or asset.get_class().get_name() != class_name:
        raise RuntimeError(f"required {class_name} unavailable: {path}")
    return asset


def apply_skotukeda_straight_bangs_v238():
    if REPORT.exists() or unreal.EditorAssetLibrary.does_asset_exist(TARGET):
        raise RuntimeError("refusing to overwrite immutable v238 output")
    _require(SOURCE, "MetaHumanCharacter")
    hair = _require(HAIR, "MetaHumanWardrobeItem")
    character = unreal.EditorAssetLibrary.duplicate_asset(SOURCE, TARGET)
    if character is None or character.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError("failed to duplicate Skotukeda MetaHumanCharacter")

    item_key = character.internal_collection.try_add_item_from_wardrobe_item("Hair", hair)
    selection = unreal.MetaHumanPipelineSlotSelection(
        slot_name="Hair", selected_item=item_key
    )
    if not character.internal_collection.default_instance.try_add_slot_selection(selection):
        raise RuntimeError("MetaHuman Hair slot rejected StraightBangs selection")

    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    if not subsystem.try_add_object_to_edit(character):
        raise RuntimeError("failed to initialize v238 character")
    try:
        subsystem.assemble_for_preview(character=character)
        if not unreal.EditorAssetLibrary.save_loaded_asset(character, only_if_is_dirty=False):
            raise RuntimeError("failed to save v238 character")
    finally:
        if subsystem.is_object_added_for_editing(character):
            subsystem.remove_object_to_edit(character)

    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v238",
        "state": "built-draft-metahuman-editor-hair-variant",
        "sourceCharacter": SOURCE,
        "targetCharacter": TARGET,
        "sourceModified": False,
        "wardrobeSlot": "Hair",
        "wardrobeItem": HAIR,
        "applicationMethod": "MetaHuman Wardrobe slot plus assemble_for_preview",
        "automaticApproval": False,
        "productionReady": False,
    }, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v238 StraightBangs variant saved: {TARGET}")
    unreal.SystemLibrary.quit_editor()


apply_skotukeda_straight_bangs_v238()
