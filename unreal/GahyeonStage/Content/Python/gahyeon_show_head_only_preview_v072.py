"""Open the immutable v072 preview map and enter PIE for desktop review."""

import unreal


TARGET_MAP = "/Game/Gahyeon/CharacterPipeline/v072/Preview/L_Gahyeon_HeadOnly_v072"
_callback = None
_ticks = 0


def _start_preview(_delta_seconds):
    global _callback, _ticks
    _ticks += 1
    if _ticks < 30:
        return
    handle = _callback
    _callback = None
    unreal.unregister_slate_post_tick_callback(handle)
    subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    subsystem.editor_play_simulate()
    unreal.log("Gahyeon v072 desktop PIE preview started")


def show_head_only_preview_v072():
    global _callback
    world = unreal.EditorLoadingAndSavingUtils.load_map(TARGET_MAP)
    if world is None:
        raise RuntimeError(f"failed to load v072 preview map: {TARGET_MAP}")
    _callback = unreal.register_slate_post_tick_callback(_start_preview)


show_head_only_preview_v072()
