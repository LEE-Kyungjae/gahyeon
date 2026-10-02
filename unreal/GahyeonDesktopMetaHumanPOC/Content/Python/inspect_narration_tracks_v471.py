"""Measure body/head motion carried by the cleaned narration donor."""

import json
import math
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
ANIMATION_PATH = "/Game/LivingCharacterPOC/v374/Donors/NarrationClean/Narration_Clean_v001_Anim"
OUTPUT = ROOT / "artifacts/living-character-poc-v471-narration-track-diagnostic/report.json"
BONES = (
    "Hips", "Spine", "Spine1", "Spine2", "Neck", "Head",
    "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand",
    "RightShoulder", "RightArm", "RightForeArm", "RightHand",
    "LeftUpLeg", "LeftLeg", "LeftFoot", "RightUpLeg", "RightLeg", "RightFoot",
)


def rotation_delta(first, other):
    dot = abs(first.x * other.x + first.y * other.y + first.z * other.z + first.w * other.w)
    return math.degrees(2.0 * math.acos(max(-1.0, min(1.0, dot))))


def inspect_narration_tracks_v471():
    if OUTPUT.exists():
        raise FileExistsError(OUTPUT)
    animation = unreal.load_asset(ANIMATION_PATH)
    if animation is None:
        raise RuntimeError(f"missing animation: {ANIMATION_PATH}")
    count = int(animation.get_editor_property("number_of_sampled_keys"))
    frames = tuple(round((count - 1) * fraction / 8) for fraction in range(9))
    tracks = {}
    for bone in BONES:
        poses = [unreal.AnimationLibrary.get_bone_pose_for_frame(animation, bone, frame, False) for frame in frames]
        tracks[bone] = {
            "maxRotationDeltaDegrees": max(rotation_delta(poses[0].rotation, pose.rotation) for pose in poses),
            "maxTranslationDelta": max(
                math.sqrt(
                    (poses[0].translation.x - pose.translation.x) ** 2
                    + (poses[0].translation.y - pose.translation.y) ** 2
                    + (poses[0].translation.z - pose.translation.z) ** 2
                )
                for pose in poses
            ),
        }
    report = {
        "schemaVersion": 1,
        "iteration": "v471",
        "status": "diagnostic-complete",
        "animation": ANIMATION_PATH,
        "skeleton": str(animation.get_editor_property("skeleton").get_path_name()),
        "sampledKeys": count,
        "frames": frames,
        "tracks": tracks,
        "humanApproved": False,
        "releaseEligible": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("NARRATION_TRACKS_V471=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


inspect_narration_tracks_v471()
