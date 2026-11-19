"""Create an immutable short Diana idle QA sequence from the validated v051 setup."""

import json
from pathlib import Path

import unreal


SOURCE_SEQUENCE = "/Game/Gahyeon/Character2/Diana/v051/Sequence/LS_Diana_VisiblePrimaryChain_v051"
TARGET_SEQUENCE = "/Game/Gahyeon/Character2/Diana/v342/Sequence/LS_Diana_IdleQA_v342"
MAP = "/Game/Gahyeon/Character2/Diana/v050/QA/L_Diana_VisiblePrimaryChain_v050"
ANIMATION = (
    "/Game/Gahyeon/Character2/Diana/v040/Animation/"
    "AS_Diana_Idle_v244_PrimaryLegs_v040"
)
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v342-diana-idle-sequence/report.json"
)


def build_diana_idle_qa_v342():
    if unreal.EditorAssetLibrary.does_asset_exist(TARGET_SEQUENCE):
        raise RuntimeError(f"refusing to overwrite immutable sequence: {TARGET_SEQUENCE}")
    animation = unreal.load_asset(ANIMATION)
    if unreal.load_asset(SOURCE_SEQUENCE) is None or animation is None:
        raise RuntimeError("Diana source sequence or idle animation unavailable")
    sequence = unreal.EditorAssetLibrary.duplicate_asset(SOURCE_SEQUENCE, TARGET_SEQUENCE)
    if sequence is None:
        raise RuntimeError("failed to duplicate Diana QA sequence")
    sequence.set_playback_start(1)
    sequence.set_playback_end(31)
    animation_sections = []
    for binding in sequence.get_bindings():
        for track in binding.get_tracks():
            if isinstance(track, unreal.MovieSceneSkeletalAnimationTrack):
                for section in track.get_sections():
                    section.params.animation = animation
                    section.set_range(0, 31)
                    animation_sections.append(str(binding.get_name()))
    if len(animation_sections) != 1:
        raise RuntimeError(f"expected one animation section, got {animation_sections}")
    if not unreal.EditorAssetLibrary.save_loaded_asset(sequence, only_if_is_dirty=False):
        raise RuntimeError("failed to save Diana idle QA sequence")
    report = {
        "schemaVersion": 1,
        "iteration": "v342",
        "status": "draft-idle-qa-ready",
        "sourceSequence": SOURCE_SEQUENCE,
        "sequence": TARGET_SEQUENCE,
        "map": MAP,
        "animation": ANIMATION,
        "playbackFrames": [1, 31],
        "hypothesis": (
            "The idle source separates persistent retarget and clothing auxiliary-bone "
            "defects from the raised-arm walk/run source poses."
        ),
        "identityChanged": False,
        "visualValidationPending": True,
        "humanApproved": False,
        "productionReady": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("DIANA_V342_IDLE=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


build_diana_idle_qa_v342()
