"""Measure clean-target retarget tracks and skeleton compatibility."""

import json
import math
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
OUTPUT = ROOT / "artifacts/living-character-poc-v456-hayley-clean-retarget-diagnostic/report.json"
MESH = "/Game/LivingCharacterPOC/v448/Characters/HayleyBindClean/Hayley_BindPoseClean_v447"
ANIMATIONS = (
    ("explain", "/Game/LivingCharacterPOC/v451/Animation/AS_HayleyClean_HandsForward_v451"),
    ("stand-sit", "/Game/LivingCharacterPOC/v452/Animation/AS_HayleyClean_StandSit_v452"),
)
BONES = ("pelvis", "spine", "lShoulder", "lForearm", "lHand", "rShoulder", "rForearm", "rHand", "lThigh", "lShin", "lFoot")


def rotation_delta(first, other):
    dot = abs(first.x * other.x + first.y * other.y + first.z * other.z + first.w * other.w)
    return math.degrees(2.0 * math.acos(max(-1.0, min(1.0, dot))))


def inspect_clean_retarget_v456():
    if OUTPUT.exists():
        raise FileExistsError(f"refusing to overwrite immutable report: {OUTPUT}")
    mesh = unreal.load_asset(MESH)
    if mesh is None:
        raise RuntimeError(f"missing mesh: {MESH}")
    mesh_skeleton = mesh.get_editor_property("skeleton")
    motions = []
    for label, path in ANIMATIONS:
        animation = unreal.load_asset(path)
        if animation is None:
            raise RuntimeError(f"missing animation: {path}")
        animation_skeleton = animation.get_editor_property("skeleton")
        count = int(animation.get_editor_property("number_of_sampled_keys"))
        frames = (0, max(0, (count - 1) // 2), max(0, count - 1))
        tracks = {}
        for bone in BONES:
            poses = [unreal.AnimationLibrary.get_bone_pose_for_frame(animation, bone, frame, False) for frame in frames]
            tracks[bone] = {
                "rotationDeltaDegrees": [rotation_delta(poses[0].rotation, pose.rotation) for pose in poses],
                "translations": [[pose.translation.x, pose.translation.y, pose.translation.z] for pose in poses],
            }
        motions.append({
            "label": label,
            "path": path,
            "sampledKeys": count,
            "frames": frames,
            "skeleton": str(animation_skeleton.get_path_name()),
            "matchesMeshSkeleton": animation_skeleton == mesh_skeleton,
            "tracks": tracks,
        })
    report = {
        "schemaVersion": 1,
        "iteration": "v456",
        "status": "diagnostic-complete",
        "mesh": MESH,
        "meshSkeleton": str(mesh_skeleton.get_path_name()),
        "motions": motions,
        "humanApproved": False,
        "releaseEligible": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("HAYLEY_CLEAN_RETARGET_DIAGNOSTIC=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


inspect_clean_retarget_v456()
