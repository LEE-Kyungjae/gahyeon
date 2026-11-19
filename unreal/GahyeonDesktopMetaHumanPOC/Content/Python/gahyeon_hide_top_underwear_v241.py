"""Disable MetaHuman's top-underwear skin layer on a v240 working copy."""

import json
from pathlib import Path

import unreal


SOURCE = "/Game/Gahyeon/CharacterPipeline/v240/Character/MHC_Skotukeda_CenterPart_v240"
TARGET = "/Game/Gahyeon/CharacterPipeline/v241/Character/MHC_Skotukeda_CenterPart_NoTopUnderwear_v241"
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v241-metahuman-no-top-underwear/build-report.json"
)


def hide_top_underwear_v241():
    if REPORT.exists() or unreal.EditorAssetLibrary.does_asset_exist(TARGET):
        raise RuntimeError("refusing to overwrite immutable v241 output")
    source = unreal.load_asset(SOURCE)
    if source is None or source.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError(f"source MetaHumanCharacter unavailable: {SOURCE}")
    character = unreal.EditorAssetLibrary.duplicate_asset(SOURCE, TARGET)
    if character is None or character.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError("failed to duplicate v240 MetaHumanCharacter")

    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    if not subsystem.try_add_object_to_edit(character):
        raise RuntimeError("failed to initialize v241 character")
    try:
        skin_settings = character.get_editor_property("skin_settings")
        skin = skin_settings.get_editor_property("skin")
        before = bool(skin.get_editor_property("show_top_underwear"))
        skin.set_editor_property("show_top_underwear", False)
        skin_settings.set_editor_property("skin", skin)
        subsystem.commit_skin_settings(character, skin_settings)
        subsystem.assemble_for_preview(character=character)
        after_settings = character.get_editor_property("skin_settings")
        after = bool(
            after_settings.get_editor_property("skin").get_editor_property(
                "show_top_underwear"
            )
        )
        if after:
            raise RuntimeError("MetaHuman top-underwear skin property remained enabled")
        if not unreal.EditorAssetLibrary.save_loaded_asset(character, only_if_is_dirty=False):
            raise RuntimeError("failed to save v241 character")
    finally:
        if subsystem.is_object_added_for_editing(character):
            subsystem.remove_object_to_edit(character)

    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v241",
        "status": "draft",
        "hypothesis": (
            "The clavicle tank-top residue is MetaHuman's Show Top Underwear skin layer, "
            "not a remaining wardrobe mesh."
        ),
        "sourceCharacter": SOURCE,
        "targetCharacter": TARGET,
        "sourceModified": False,
        "hairPreserved": "WI_Hair_L_Straight",
        "editorControl": "Materials > Skin > Show Top Underwear",
        "showTopUnderwearBefore": before,
        "showTopUnderwearAfter": after,
        "automaticApproval": False,
        "productionReady": False,
    }, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v241 no-top-underwear MetaHuman saved: {TARGET}")
    unreal.SystemLibrary.quit_editor()


hide_top_underwear_v241()
