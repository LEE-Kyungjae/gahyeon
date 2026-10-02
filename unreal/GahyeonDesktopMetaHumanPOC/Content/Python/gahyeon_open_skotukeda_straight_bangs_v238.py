"""Open the immutable v238 hair variant in MetaHuman Character Editor."""

import unreal


TARGET = "/Game/Gahyeon/CharacterPipeline/v238/Character/MHC_Skotukeda_StraightBangs_v238"
_callback_v238 = None


def open_skotukeda_straight_bangs_v238(_delta_seconds):
    global _callback_v238
    unreal.unregister_slate_post_tick_callback(_callback_v238)
    _callback_v238 = None
    character = unreal.load_asset(TARGET)
    if character is None or character.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError(f"v238 MetaHumanCharacter unavailable: {TARGET}")
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).open_editor_for_assets([character])
    unreal.log(f"Gahyeon v238 opened in MetaHuman Character Editor: {TARGET}")


_callback_v238 = unreal.register_slate_post_tick_callback(open_skotukeda_straight_bangs_v238)
