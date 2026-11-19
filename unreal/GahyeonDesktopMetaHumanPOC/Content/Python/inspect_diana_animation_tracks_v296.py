"""Measure source and retargeted Diana bone-track motion without changing assets."""

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
    "v296-diana-animation-track-inspection/report.json"
)
SOURCE_BONES = [
    "pelvis",
    "spine_01",
    "spine_03",
    "neck_01",
    "head",
    "clavicle_l",
    "upperarm_l",
    "lowerarm_l",
    "hand_l",
    "clavicle_r",
    "upperarm_r",
    "lowerarm_r",
    "hand_r",
    "thigh_l",
    "calf_l",
    "foot_l",
    "thigh_r",
    "calf_r",
    "foot_r",
]
TARGET_BONES = [
    "hip",
    "spine_0",
    "neck_0",
    "head_002",
    "l_shoulder",
    "l_upperarm",
    "l_forearm",
    "l_hand",
    "r_shoulder",
    "r_upperarm",
    "r_forearm",
    "r_hand",
    "l_thigh_001",
    "l_shin",
    "l_foot",
    "r_thigh_001",
    "r_shin",
    "r_foot",
]


def quat_angle_degrees(first, other):
    dot = abs(
        first.x * other.x
        + first.y * other.y
        + first.z * other.z
        + first.w * other.w
    )
    return math.degrees(2.0 * math.acos(max(-1.0, min(1.0, dot))))


def inspect_animation(path, requested_bones):
    animation = unreal.EditorAssetLibrary.load_asset(path)
    if animation is None:
        raise RuntimeError(f"animation unavailable: {path}")
    track_names = {str(name) for name in unreal.AnimationLibrary.get_animation_track_names(animation)}
    bones = {}
    for bone in requested_bones:
        if bone not in track_names:
            bones[bone] = {"trackPresent": False}
            continue
        rotations = list(
            unreal.AnimationLibrary.get_raw_track_rotation_data(animation, bone)
        )
        translations = list(
            unreal.AnimationLibrary.get_raw_track_position_data(animation, bone)
        )
        max_rotation = 0.0
        if rotations:
            max_rotation = max(
                quat_angle_degrees(rotations[0], rotation) for rotation in rotations
            )
        max_translation = 0.0
        if translations:
            first = translations[0]
            max_translation = max(
                math.sqrt(
                    (value.x - first.x) ** 2
                    + (value.y - first.y) ** 2
                    + (value.z - first.z) ** 2
                )
                for value in translations
            )
        bones[bone] = {
            "trackPresent": True,
            "rotationKeys": len(rotations),
            "translationKeys": len(translations),
            "maxRotationDeltaDegrees": round(max_rotation, 4),
            "maxTranslationDeltaCm": round(max_translation, 4),
        }
    return {
        "path": path,
        "trackCount": len(track_names),
        "tracks": sorted(track_names),
        "requestedBones": bones,
    }


report = {
    "schemaVersion": 1,
    "iteration": "v296",
    "status": "read-only-animation-track-inspection",
    "source": inspect_animation(SOURCE, SOURCE_BONES),
    "target": inspect_animation(TARGET, TARGET_BONES),
    "mutatedAssets": [],
    "humanApproved": False,
    "productionReady": False,
}
OUTPUT.parent.mkdir(parents=True, exist_ok=False)
OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("DIANA_V296_TRACK_INSPECTION=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
