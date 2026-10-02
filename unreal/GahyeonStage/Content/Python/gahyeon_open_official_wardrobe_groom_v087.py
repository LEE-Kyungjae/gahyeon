"""Open the immutable v087 MetaHuman Character for human visual inspection."""

import unreal


CHARACTER = "/Game/Gahyeon/CharacterPipeline/v087/Character/MHC_Skotukeda_WardrobeGroom_v087"
_callback = None


def open_preview(_delta_seconds):
    global _callback
    unreal.unregister_slate_post_tick_callback(_callback)
    _callback = None
    character = unreal.load_asset(CHARACTER)
    if character is None or character.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError(f"v087 MetaHuman Character unavailable: {CHARACTER}")
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).open_editor_for_assets([character])
    unreal.log(f"Gahyeon v087 opened for visual inspection: {CHARACTER}")


_callback = unreal.register_slate_post_tick_callback(open_preview)
