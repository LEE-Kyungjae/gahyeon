"""Sample evaluated Diana animation poses without changing Unreal assets."""

import json
import math
from pathlib import Path

import unreal


SOURCE = (
    "/Game/Gahyeon/CharacterPipeline/v244/Animation/"
    "AS_Gahyeon_RunForward_v244"
)
TARGET = (
    "/Game/Gahyeon/Character2/Diana/v040/Animation/"
    "AS_Diana_RunForward_v244_PrimaryLegs_v040"
)
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v297-diana-animation-pose-inspection/report.json"
)
SOURCE_BONES = [
    "pelvis", "spine_01", "spine_03", "neck_01", "head",
    "clavicle_l", "upperarm_l", "lowerarm_l", "hand_l",
    "clavicle_r", "upperarm_r", "lowerarm_r", "hand_r",
    "thigh_l", "calf_l", "foot_l", "thigh_r", "calf_r", "foot_r",
]
TARGET_BONES = [
    "hip", "spine_0", "neck_0", "head_002",
    "l_shoulder", "l_upperarm", "l_forearm", "l_hand",
    "r_shoulder", "r_upperarm", "r_forearm", "r_hand",
    "l_thigh_001", "l_shin", "l_foot", "r_thigh_001", "r_shin", "r_foot",
]


def quat_angle_degrees(first, other):
    dot = abs(
        first.x * other.x
        + first.y * other.y
        + first.z * other.z
        + first.w * other.w
    )
    return math.degrees(2.0 * math.acos(max(-1.0, min(1.0, dot))))


def vector_distance(first, other):
    return math.sqrt(
        (other.x - first.x) ** 2
        + (other.y - first.y) ** 2
        + (other.z - first.z) ** 2
    )


def inspect_pose_samples(path, requested_bones):
    animation = unreal.EditorAssetLibrary.load_asset(path)
    if animation is None:
        raise RuntimeError(f"animation unavailable: {path}")

    frame_count = int(unreal.AnimationLibrary.get_num_frames(animation))
    if frame_count < 2:
        raise RuntimeError(f"animation has too few frames: {path}: {frame_count}")
    sample_frames = sorted(
        {0, frame_count // 4, frame_count // 2, (frame_count * 3) // 4, frame_count - 1}
    )
    track_names = {
        str(name)
        for name in unreal.AnimationLibrary.get_animation_track_names(animation)
    }
    bones = {}
    for bone in requested_bones:
        if bone not in track_names:
            bones[bone] = {"trackPresent": False}
            continue
        poses = [
            unreal.AnimationLibrary.get_bone_pose_for_frame(
                animation, bone, frame, False
            )
            for frame in sample_frames
        ]
        rotations = [pose.rotation for pose in poses]
        translations = [pose.translation for pose in poses]
        bones[bone] = {
            "trackPresent": True,
            "sampledFrames": sample_frames,
            "maxRotationDeltaDegrees": round(
                max(quat_angle_degrees(rotations[0], value) for value in rotations),
                4,
            ),
            "maxTranslationDeltaCm": round(
                max(vector_distance(translations[0], value) for value in translations),
                4,
            ),
        }
    return {
        "path": path,
        "frameCount": frame_count,
        "sampledFrames": sample_frames,
        "trackCount": len(track_names),
        "requestedBones": bones,
    }


report = {
    "schemaVersion": 1,
    "iteration": "v297",
    "status": "read-only-evaluated-pose-inspection",
    "source": inspect_pose_samples(SOURCE, SOURCE_BONES),
    "target": inspect_pose_samples(TARGET, TARGET_BONES),
    "mutatedAssets": [],
    "humanApproved": False,
    "productionReady": False,
}
OUTPUT.parent.mkdir(parents=True, exist_ok=False)
OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("DIANA_V297_POSE_INSPECTION=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
