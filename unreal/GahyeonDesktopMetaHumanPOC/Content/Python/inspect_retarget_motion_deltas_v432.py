"""Compare compressed source and Hayley target motion at three normalized phases."""

import json
import math
from pathlib import Path

import unreal


PAIRS = (
    ("idle", "/Game/LivingCharacterPOC/v371/Donors/CyberIdle/Idle_Anim", "/Game/LivingCharacterPOC/v428/Animation/AS_Hayley_CyberIdle_v428", ("pelvis", "hand_l", "hand_r", "foot_l", "foot_r"), ("pelvis", "lhand", "rhand", "lfoot", "rfoot")),
    ("explain", "/Game/LivingCharacterPOC/v371/Donors/HandsForward/Hands_Forward_Gesture_Anim", "/Game/LivingCharacterPOC/v429/Animation/AS_Hayley_HandsForward_v429", ("Hips", "LeftHand", "RightHand", "LeftFoot", "RightFoot"), ("pelvis", "lhand", "rhand", "lfoot", "rfoot")),
    ("stand-sit", "/Game/LivingCharacterPOC/v374/Donors/StandSitClean/StandSit_Clean_v001_Anim", "/Game/LivingCharacterPOC/v430/Animation/AS_Hayley_StandSit_v430", ("Hips", "LeftHand", "RightHand", "LeftFoot", "RightFoot"), ("pelvis", "lhand", "rhand", "lfoot", "rfoot")),
)
OUTPUT = Path("/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v432-retarget-motion-deltas/report.json")


def rotation_delta(first, other):
    dot = abs(first.x * other.x + first.y * other.y + first.z * other.z + first.w * other.w)
    return math.degrees(2.0 * math.acos(max(-1.0, min(1.0, dot))))


def vector_delta(first, other):
    return math.sqrt((first.x-other.x)**2 + (first.y-other.y)**2 + (first.z-other.z)**2)


def inspect_sequence(path, bones):
    animation = unreal.load_asset(path)
    if animation is None:
        raise RuntimeError(f"animation unavailable: {path}")
    count = int(animation.get_editor_property("number_of_sampled_keys"))
    frames = (0, max(0, (count - 1) // 2), max(0, count - 1))
    records = {}
    for bone in bones:
        poses = [unreal.AnimationLibrary.get_bone_pose_for_frame(animation, bone, frame, False) for frame in frames]
        records[bone] = {
            "translationDelta": [vector_delta(poses[0].translation, pose.translation) for pose in poses],
            "rotationDeltaDegrees": [rotation_delta(poses[0].rotation, pose.rotation) for pose in poses],
        }
    return {"path": path, "sampledKeys": count, "frames": frames, "bones": records}


def inspect_retarget_motion_deltas_v432():
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to overwrite immutable v432 report: {OUTPUT}")
    motions = []
    for label, source, target, source_bones, target_bones in PAIRS:
        motions.append({"label": label, "source": inspect_sequence(source, source_bones), "target": inspect_sequence(target, target_bones)})
    report = {
        "schemaVersion": 1, "iteration": "v432", "status": "compressed-motion-deltas-measured",
        "motions": motions, "mutatedAssets": [], "humanApproved": False, "releaseEligible": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("RETARGET_V432_DELTAS=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


inspect_retarget_motion_deltas_v432()
