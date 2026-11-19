"""Verify which Cyber Idle skeleton actually owns animated tracks."""

import json
import math
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
ANIMATION_PATH = "/Game/LivingCharacterPOC/v371/Donors/CyberIdle/Idle_Anim"
OUTPUT = ROOT / "artifacts/living-character-poc-v465-cyber-idle-track-diagnostic/report.json"
BONES = (
    "prefix_pelvis", "prefix_spine_01", "prefix_spine_02", "prefix_spine_03",
    "prefix_neck_01", "prefix_head", "prefix_clavicle_l", "prefix_upperarm_l",
    "prefix_lowerarm_l", "prefix_hand_l", "prefix_thigh_l", "prefix_calf_l", "prefix_foot_l",
)


def rotation_delta(first, other):
    dot = abs(first.x * other.x + first.y * other.y + first.z * other.z + first.w * other.w)
    return math.degrees(2.0 * math.acos(max(-1.0, min(1.0, dot))))


def inspect_cyber_idle_v465():
    if OUTPUT.exists():
        raise FileExistsError(OUTPUT)
    animation = unreal.load_asset(ANIMATION_PATH)
    if animation is None:
        raise RuntimeError(f"missing animation: {ANIMATION_PATH}")
    count = int(animation.get_editor_property("number_of_sampled_keys"))
    frames = (0, max(0, (count - 1) // 4), max(0, (count - 1) // 2), max(0, count - 1))
    tracks = {}
    for bone in BONES:
        poses = [unreal.AnimationLibrary.get_bone_pose_for_frame(animation, bone, frame, False) for frame in frames]
        tracks[bone] = {
            "rotationDeltaDegrees": [rotation_delta(poses[0].rotation, pose.rotation) for pose in poses],
            "translationDelta": [
                math.sqrt(
                    (poses[0].translation.x - pose.translation.x) ** 2
                    + (poses[0].translation.y - pose.translation.y) ** 2
                    + (poses[0].translation.z - pose.translation.z) ** 2
                )
                for pose in poses
            ],
        }
    skeleton = animation.get_editor_property("skeleton")
    report = {
        "schemaVersion": 1,
        "iteration": "v465",
        "status": "diagnostic-complete",
        "animation": ANIMATION_PATH,
        "skeleton": str(skeleton.get_path_name()),
        "sampledKeys": count,
        "frames": frames,
        "tracks": tracks,
        "humanApproved": False,
        "releaseEligible": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("CYBER_IDLE_V465=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


inspect_cyber_idle_v465()
