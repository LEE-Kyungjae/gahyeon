"""Cycle Diana's corrected idle, walk, and run clips without saving the QA sequence."""

import time

import unreal


CLIPS = (
    ("IDLE", "/Game/Gahyeon/Character2/Diana/v375/Animation/AS_Diana_Idle_v244_ComponentCopy_v375"),
    ("WALK", "/Game/Gahyeon/Character2/Diana/v375/Animation/AS_Diana_WalkForward_v244_ComponentCopy_v375"),
    ("RUN", "/Game/Gahyeon/Character2/Diana/v375/Animation/AS_Diana_RunForward_v244_ComponentCopy_v375"),
)
MAP = "/Game/Gahyeon/Character2/Diana/v050/QA/L_Diana_VisiblePrimaryChain_v050"
SEQUENCE = "/Game/Gahyeon/Character2/Diana/v346/Sequence/LS_Diana_APoseIdleQA_v346"
SWITCH_SECONDS = 6.0

_state = {"index": -1, "changed_at": 0.0, "callback": None}


def _animation_section():
    sequence = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
    if sequence is None:
        raise RuntimeError("No Diana Level Sequence is open")
    sections = []
    for binding in sequence.get_bindings():
        for track in binding.get_tracks():
            if isinstance(track, unreal.MovieSceneSkeletalAnimationTrack):
                sections.extend(track.get_sections())
    if len(sections) != 1:
        raise RuntimeError(f"Expected one Diana animation section, found {len(sections)}")
    return sections[0]


def _show_clip(index):
    label, path = CLIPS[index]
    animation = unreal.load_asset(path)
    if animation is None:
        raise RuntimeError(f"Diana animation is unavailable: {path}")
    section = _animation_section()
    section.params.animation = animation
    section.set_range(1, 31)
    unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(1)
    unreal.LevelSequenceEditorBlueprintLibrary.force_update()
    unreal.LevelSequenceEditorBlueprintLibrary.play()
    unreal.log(f"DIANA_ACTION_PLAYING={label}:{path}")


def _cycle(_delta_seconds):
    now = time.monotonic()
    if now - _state["changed_at"] < SWITCH_SECONDS:
        return
    _state["index"] = (_state["index"] + 1) % len(CLIPS)
    _state["changed_at"] = now
    _show_clip(_state["index"])


unreal.EditorLoadingAndSavingUtils.load_map(MAP)
sequence = unreal.load_asset(SEQUENCE)
if sequence is None or not unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(sequence):
    raise RuntimeError(f"Could not open Diana action sequence: {SEQUENCE}")
_state["callback"] = unreal.register_slate_post_tick_callback(_cycle)
_cycle(0.0)
