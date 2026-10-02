"""Measure the compressed cjaw pose at authored calibration frames."""

import json
import math
from pathlib import Path

import unreal


ANIMATION = "/Game/LivingCharacterPOC/v391/JawAxisSweepImport/Hayley_JawAxisSweep_Full_v390_Anim"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/"
    "living-character-poc-v397-hayley-jaw-compressed-pose/report.json"
)
FRAMES = (0, 9, 19, 29, 39, 49, 58)


def quat_angle_degrees_v397(first, other):
    dot = abs(
        first.x * other.x
        + first.y * other.y
        + first.z * other.z
        + first.w * other.w
    )
    return math.degrees(2.0 * math.acos(max(-1.0, min(1.0, dot))))


def inspect_hayley_jaw_compressed_pose_v397():
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to overwrite immutable v397 report: {OUTPUT}")
    animation = unreal.EditorAssetLibrary.load_asset(ANIMATION)
    if animation is None:
        raise RuntimeError(f"animation unavailable: {ANIMATION}")
    poses = [
        unreal.AnimationLibrary.get_bone_pose_for_frame(
            animation, "cjaw", frame, False
        )
        for frame in FRAMES
    ]
    deltas = [quat_angle_degrees_v397(poses[0].rotation, pose.rotation) for pose in poses]
    report = {
        "schemaVersion": 1,
        "iteration": "v397",
        "status": "compressed-jaw-pose-measured",
        "animation": ANIMATION,
        "bone": "cjaw",
        "sampledFrames": list(FRAMES),
        "rotationDeltaDegrees": deltas,
        "maxRotationDeltaDegrees": max(deltas),
        "diagnosis": (
            "compressed-track-has-motion"
            if max(deltas) > 0.5
            else "fbx-bake-or-import-produced-static-jaw"
        ),
        "humanApproved": False,
        "releaseEligible": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("HAYLEY_V397_JAW_POSE=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


inspect_hayley_jaw_compressed_pose_v397()
