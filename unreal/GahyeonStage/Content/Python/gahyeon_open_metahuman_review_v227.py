"""Open immutable v226 in MetaHuman Character Editor without building it."""

import unreal


CHARACTER = "/Game/Gahyeon/CharacterPipeline/v226/Character/MHC_Gahyeon_ExternalClay_v226"
_callback_v227 = None


def open_metahuman_review_v227(_delta_seconds):
    global _callback_v227
    unreal.unregister_slate_post_tick_callback(_callback_v227)
    _callback_v227 = None
    character = unreal.load_asset(CHARACTER)
    if character is None or character.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError(f"v226 MetaHuman unavailable: {CHARACTER}")
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).open_editor_for_assets([character])
    unreal.EditorPythonScripting.set_keep_python_script_alive(True)
    unreal.log(f"Gahyeon v227 read-only identity review opened: {CHARACTER}")


_callback_v227 = unreal.register_slate_post_tick_callback(open_metahuman_review_v227)
