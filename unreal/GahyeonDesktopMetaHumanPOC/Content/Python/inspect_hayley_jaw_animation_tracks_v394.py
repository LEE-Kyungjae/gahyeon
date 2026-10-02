"""Inspect imported Hayley jaw sweep tracks without evaluating a scene actor."""

import json
import math
from pathlib import Path

import unreal


ANIMATION = "/Game/LivingCharacterPOC/v391/JawAxisSweepImport/Hayley_JawAxisSweep_Full_v390_Anim"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/"
    "living-character-poc-v394-hayley-jaw-track-inspection/report.json"
)


def quat_angle_degrees_v394(first, other):
    dot = abs(
        first.x * other.x
        + first.y * other.y
        + first.z * other.z
        + first.w * other.w
    )
    return math.degrees(2.0 * math.acos(max(-1.0, min(1.0, dot))))


def inspect_hayley_jaw_animation_tracks_v394():
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to overwrite immutable v394 report: {OUTPUT}")
    animation = unreal.EditorAssetLibrary.load_asset(ANIMATION)
    if animation is None:
        raise RuntimeError(f"animation unavailable: {ANIMATION}")
    tracks = {
        str(name) for name in unreal.AnimationLibrary.get_animation_track_names(animation)
    }
    present = "cJaw" in tracks
    rotations = (
        list(unreal.AnimationLibrary.get_raw_track_rotation_data(animation, "cJaw"))
        if present
        else []
    )
    translations = (
        list(unreal.AnimationLibrary.get_raw_track_position_data(animation, "cJaw"))
        if present
        else []
    )
    max_rotation = (
        max(quat_angle_degrees_v394(rotations[0], value) for value in rotations)
        if rotations
        else 0.0
    )
    report = {
        "schemaVersion": 1,
        "iteration": "v394",
        "status": "read-only-jaw-track-inspection",
        "animation": ANIMATION,
        "frameCount": int(unreal.AnimationLibrary.get_num_frames(animation)),
        "trackCount": len(tracks),
        "cJaw": {
            "trackPresent": present,
            "rotationKeys": len(rotations),
            "translationKeys": len(translations),
            "maxRotationDeltaDegrees": max_rotation,
        },
        "diagnosis": (
            "imported-track-has-motion"
            if max_rotation > 0.5
            else "imported-track-missing-or-static"
        ),
        "humanApproved": False,
        "releaseEligible": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("HAYLEY_V394_JAW_TRACK=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


inspect_hayley_jaw_animation_tracks_v394()
