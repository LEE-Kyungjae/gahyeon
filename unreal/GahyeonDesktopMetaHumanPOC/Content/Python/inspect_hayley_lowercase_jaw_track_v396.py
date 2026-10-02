"""Measure the lower-cased Hayley jaw track produced by UE Interchange."""

import json
import math
from pathlib import Path

import unreal


ANIMATION = "/Game/LivingCharacterPOC/v391/JawAxisSweepImport/Hayley_JawAxisSweep_Full_v390_Anim"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/"
    "living-character-poc-v396-hayley-lowercase-jaw-track/report.json"
)


def quat_angle_degrees_v396(first, other):
    dot = abs(
        first.x * other.x
        + first.y * other.y
        + first.z * other.z
        + first.w * other.w
    )
    return math.degrees(2.0 * math.acos(max(-1.0, min(1.0, dot))))


def inspect_hayley_lowercase_jaw_track_v396():
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to overwrite immutable v396 report: {OUTPUT}")
    animation = unreal.EditorAssetLibrary.load_asset(ANIMATION)
    if animation is None:
        raise RuntimeError(f"animation unavailable: {ANIMATION}")
    rotations = list(
        unreal.AnimationLibrary.get_raw_track_rotation_data(animation, "cjaw")
    )
    positions = list(
        unreal.AnimationLibrary.get_raw_track_position_data(animation, "cjaw")
    )
    if not rotations:
        raise RuntimeError("lower-case cjaw track has no rotation keys")
    deltas = [quat_angle_degrees_v396(rotations[0], value) for value in rotations]
    report = {
        "schemaVersion": 1,
        "iteration": "v396",
        "status": "lowercase-jaw-track-measured",
        "animation": ANIMATION,
        "bone": "cjaw",
        "rotationKeys": len(rotations),
        "translationKeys": len(positions),
        "maxRotationDeltaDegrees": max(deltas),
        "keyIndicesOverOneDegree": [
            index for index, value in enumerate(deltas) if value > 1.0
        ],
        "diagnosis": "case-normalization-confirmed",
        "humanApproved": False,
        "releaseEligible": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("HAYLEY_V396_LOWERCASE_JAW=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


inspect_hayley_lowercase_jaw_track_v396()
