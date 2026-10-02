"""Build an isolated UE 5.8 MetaHuman Wardrobe groom preview.

This deliberately does not mutate an assembled Blueprint or GroomComponent.
The MetaHuman pipeline owns binding, RBF conversion, attachment, and materials.
"""

import json
from pathlib import Path

import unreal


SOURCE_CHARACTER = "/Game/Fab/MetaHuman/Skotukeda"
TARGET_CHARACTER = "/Game/Gahyeon/CharacterPipeline/v087/Character/MHC_Skotukeda_WardrobeGroom_v087"
WARDROBE_ITEM = (
    "/MetaHumanCharacter/Optional/Grooms/Bindings/Hair/"
    "WI_Hair_L_StraightBangs.WI_Hair_L_StraightBangs"
)
RECEIPT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v087-official-wardrobe-groom/build-receipt.json"
)


def require_asset(path, expected_class):
    asset = unreal.load_asset(path)
    if asset is None or asset.get_class().get_name() != expected_class:
        raise RuntimeError(f"required {expected_class} unavailable: {path}")
    return asset


def build():
    if RECEIPT.exists() or unreal.EditorAssetLibrary.does_asset_exist(TARGET_CHARACTER):
        raise RuntimeError("refusing to overwrite immutable v087 output")

    source = require_asset(SOURCE_CHARACTER, "MetaHumanCharacter")
    wardrobe_item = require_asset(WARDROBE_ITEM, "MetaHumanWardrobeItem")
    character = unreal.EditorAssetLibrary.duplicate_asset(SOURCE_CHARACTER, TARGET_CHARACTER)
    if character is None or character.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError("failed to duplicate the source MetaHuman Character")

    item_key = character.internal_collection.try_add_item_from_wardrobe_item(
        "Hair", wardrobe_item
    )

    selection = unreal.MetaHumanPipelineSlotSelection(
        slot_name="Hair", selected_item=item_key
    )
    if not character.internal_collection.default_instance.try_add_slot_selection(selection):
        raise RuntimeError("Hair slot selection was rejected")

    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    if not subsystem.try_add_object_to_edit(character):
        raise RuntimeError("MetaHuman Character could not be opened for editing")

    try:
        # This is the critical operation. It lets the UE 5.8 pipeline generate and
        # apply the groom assembly output for the character's actual target meshes.
        subsystem.assemble_for_preview(character=character)
        if not unreal.EditorAssetLibrary.save_loaded_asset(character, only_if_is_dirty=False):
            raise RuntimeError("failed to save the isolated v087 character")
    finally:
        if subsystem.is_object_added_for_editing(character):
            subsystem.remove_object_to_edit(character)

    RECEIPT.parent.mkdir(parents=True, exist_ok=False)
    RECEIPT.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "iteration": "v087",
                "state": "draft-official-wardrobe-groom-preview-assembled",
                "sourceCharacter": SOURCE_CHARACTER,
                "targetCharacter": TARGET_CHARACTER,
                "wardrobeItem": WARDROBE_ITEM,
                "slot": "Hair",
                "assemblyOperation": "MetaHumanCharacterEditorSubsystem.assemble_for_preview",
                "directComponentMutation": False,
                "manualTransformOffset": False,
                "productionReady": False,
                "automaticApproval": False,
            },
            indent=2,
        )
        + "\n"
    )
    unreal.log(f"Gahyeon v087 official Wardrobe groom preview assembled: {TARGET_CHARACTER}")


build()
