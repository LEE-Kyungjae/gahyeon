"""Open the immutable Fab source in MetaHuman Character Editor for visual evidence."""

import unreal


SOURCE = "/Game/Fab/MetaHuman/Skotukeda"
_callback_v173 = None


def open_golden_source_v173(_delta_seconds):
    global _callback_v173
    unreal.unregister_slate_post_tick_callback(_callback_v173)
    _callback_v173 = None
    character = unreal.load_asset(SOURCE)
    if character is None or character.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError(f"Fab source MetaHuman unavailable: {SOURCE}")
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).open_editor_for_assets([character])
    unreal.log(f"Gahyeon v173 immutable source opened without save: {SOURCE}")


_callback_v173 = unreal.register_slate_post_tick_callback(open_golden_source_v173)
