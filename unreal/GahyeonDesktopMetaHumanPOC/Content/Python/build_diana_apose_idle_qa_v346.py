"""Build a short visual QA sequence for Diana's v345 A-pose idle candidate."""

import json
from pathlib import Path

import unreal


SOURCE_SEQUENCE = "/Game/Gahyeon/Character2/Diana/v051/Sequence/LS_Diana_VisiblePrimaryChain_v051"
TARGET_SEQUENCE = "/Game/Gahyeon/Character2/Diana/v346/Sequence/LS_Diana_APoseIdleQA_v346"
MAP = "/Game/Gahyeon/Character2/Diana/v050/QA/L_Diana_VisiblePrimaryChain_v050"
ANIMATION = "/Game/Gahyeon/Character2/Diana/v345/Animation/AS_Diana_Idle_v244_APose_v345"
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v346-diana-apose-idle-sequence/report.json"
)


def build_diana_apose_idle_qa_v346():
    if unreal.EditorAssetLibrary.does_asset_exist(TARGET_SEQUENCE):
        raise RuntimeError(f"refusing to overwrite immutable sequence: {TARGET_SEQUENCE}")
    animation = unreal.load_asset(ANIMATION)
    if unreal.load_asset(SOURCE_SEQUENCE) is None or animation is None:
        raise RuntimeError("Diana source sequence or A-pose idle unavailable")
    sequence = unreal.EditorAssetLibrary.duplicate_asset(SOURCE_SEQUENCE, TARGET_SEQUENCE)
    if sequence is None:
        raise RuntimeError("failed to duplicate Diana QA sequence")
    sequence.set_playback_start(1)
    sequence.set_playback_end(31)
    sections = []
    for binding in sequence.get_bindings():
        for track in binding.get_tracks():
            if isinstance(track, unreal.MovieSceneSkeletalAnimationTrack):
                for section in track.get_sections():
                    section.params.animation = animation
                    section.set_range(0, 31)
                    sections.append(str(binding.get_name()))
    if len(sections) != 1:
        raise RuntimeError(f"expected one animation section, got {sections}")
    if not unreal.EditorAssetLibrary.save_loaded_asset(sequence, only_if_is_dirty=False):
        raise RuntimeError("failed to save Diana A-pose idle sequence")
    report = {
        "schemaVersion": 1,
        "iteration": "v346",
        "status": "draft-apose-idle-qa-ready",
        "sequence": TARGET_SEQUENCE,
        "map": MAP,
        "animation": ANIMATION,
        "playbackFrames": [1, 31],
        "hypothesis": "The v344 target retarget pose lowers Diana's arms in idle.",
        "identityChanged": False,
        "visualValidationPending": True,
        "humanApproved": False,
        "productionReady": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("DIANA_V346_APOSE_IDLE=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


build_diana_apose_idle_qa_v346()
