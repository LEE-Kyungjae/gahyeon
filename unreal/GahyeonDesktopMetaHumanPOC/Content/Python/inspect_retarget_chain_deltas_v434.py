"""Measure source and target body-chain motion retained by the Hayley retargets."""

import json
import math
from pathlib import Path

import unreal


PAIRS = (
    ("explain", "/Game/LivingCharacterPOC/v371/Donors/HandsForward/Hands_Forward_Gesture_Anim", "/Game/LivingCharacterPOC/v429/Animation/AS_Hayley_HandsForward_v429"),
    ("stand-sit", "/Game/LivingCharacterPOC/v374/Donors/StandSitClean/StandSit_Clean_v001_Anim", "/Game/LivingCharacterPOC/v430/Animation/AS_Hayley_StandSit_v430"),
)
SOURCE_BONES = ("Hips", "Spine", "Spine1", "Spine2", "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand", "RightShoulder", "RightArm", "RightForeArm", "RightHand", "LeftUpLeg", "LeftLeg", "LeftFoot", "RightUpLeg", "RightLeg", "RightFoot")
TARGET_BONES = ("pelvis", "spine", "spine1", "spine2", "lScapula", "lShoulder", "lForearm", "lHand", "rScapula", "rShoulder", "rForearm", "rHand", "lThigh", "lKnee", "lFoot", "rThigh", "rKnee", "rFoot")
OUTPUT = Path("/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v434-retarget-chain-deltas/report.json")


def quat_delta(first, other):
    dot = abs(first.x*other.x + first.y*other.y + first.z*other.z + first.w*other.w)
    return math.degrees(2.0 * math.acos(max(-1.0, min(1.0, dot))))


def vec_delta(first, other):
    return math.sqrt((first.x-other.x)**2 + (first.y-other.y)**2 + (first.z-other.z)**2)


def inspect(path, bones):
    animation = unreal.load_asset(path)
    if animation is None:
        raise RuntimeError(f"animation unavailable: {path}")
    count = int(animation.get_editor_property("number_of_sampled_keys"))
    frames = (0, max(0, (count-1)//4), max(0, (count-1)//2), max(0, 3*(count-1)//4), max(0, count-1))
    result = {}
    for bone in bones:
        poses = [unreal.AnimationLibrary.get_bone_pose_for_frame(animation, bone, frame, False) for frame in frames]
        result[bone] = {
            "maxRotationDeltaDegrees": max(quat_delta(poses[0].rotation, pose.rotation) for pose in poses),
            "maxTranslationDelta": max(vec_delta(poses[0].translation, pose.translation) for pose in poses),
        }
    return {"path": path, "sampledKeys": count, "frames": frames, "bones": result}


def inspect_retarget_chain_deltas_v434():
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to overwrite immutable v434 report: {OUTPUT}")
    motions = []
    for label, source, target in PAIRS:
        source_report = inspect(source, SOURCE_BONES)
        target_report = inspect(target, TARGET_BONES)
        retention = []
        for source_bone, target_bone in zip(SOURCE_BONES, TARGET_BONES):
            source_rotation = source_report["bones"][source_bone]["maxRotationDeltaDegrees"]
            target_rotation = target_report["bones"][target_bone]["maxRotationDeltaDegrees"]
            retention.append({
                "sourceBone": source_bone, "targetBone": target_bone,
                "sourceRotationDeltaDegrees": source_rotation,
                "targetRotationDeltaDegrees": target_rotation,
                "rotationRetention": target_rotation/source_rotation if source_rotation > 0.01 else None,
            })
        motions.append({"label": label, "source": source_report, "target": target_report, "retention": retention})
    report = {"schemaVersion": 1, "iteration": "v434", "status": "retarget-chain-deltas-measured", "motions": motions, "mutatedAssets": [], "humanApproved": False, "releaseEligible": False}
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("RETARGET_V434_CHAINS=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


inspect_retarget_chain_deltas_v434()
