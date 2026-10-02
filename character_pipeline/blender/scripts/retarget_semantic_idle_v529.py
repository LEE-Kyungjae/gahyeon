#!/usr/bin/env python3
"""Retarget Hayley's validated active idle to a semantic target skeleton draft."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector


ROLE_ORDER = (
    "pelvis", "spineLower", "spineMid", "spineUpper", "neck", "head",
    "clavicleL", "upperArmL", "lowerArmL", "handL",
    "clavicleR", "upperArmR", "lowerArmR", "handR",
    "thighL", "calfL", "footL", "toeL",
    "thighR", "calfR", "footR", "toeR",
)
UPPER_BODY_ROLES = (
    "spineLower", "spineMid", "spineUpper", "neck", "head",
    "clavicleL", "upperArmL", "lowerArmL", "handL",
    "clavicleR", "upperArmR", "lowerArmR", "handR",
)


def parse_args() -> argparse.Namespace:
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--motion", required=True, type=Path)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--profiles", required=True, type=Path)
    parser.add_argument("--target-id", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--iteration", default="v529")
    parser.add_argument("--pelvis-translation-factor", type=float, default=0.0)
    parser.add_argument("--upper-body-only", action="store_true")
    return parser.parse_args(values)


def import_single_armature(path: Path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path.resolve()))
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    if len(armatures) != 1:
        raise RuntimeError(f"expected one armature in {path}, found {len(armatures)}")
    return armatures[0]


def skeleton_height(armature) -> float:
    coordinates = [value for bone in armature.data.bones for value in (bone.head_local.z, bone.tail_local.z)]
    return max(coordinates) - min(coordinates)


def retarget_semantic_idle_v529(
    motion: Path,
    target: Path,
    profiles_path: Path,
    target_id: str,
    output: Path,
    report_path: Path,
    iteration: str,
    pelvis_translation_factor: float,
    upper_body_only: bool,
) -> dict[str, object]:
    for path in (motion, target, profiles_path):
        if not path.is_file():
            raise FileNotFoundError(path)
    if output.exists() or report_path.exists():
        raise FileExistsError("refusing to overwrite immutable retarget draft")
    profiles = json.loads(profiles_path.read_text(encoding="utf-8"))
    source_roles = profiles["source"]["roles"]
    target_roles = profiles["targets"][target_id]["roles"]
    rest_corrections = profiles["targets"][target_id].get("globalRestPoseCorrectionDegrees", {})

    source_armature = import_single_armature(motion)
    source_action = source_armature.animation_data.action if source_armature.animation_data else None
    if source_action is None:
        raise RuntimeError("source motion has no active action")
    source_start = int(round(source_action.frame_range[0]))
    source_end = int(round(source_action.frame_range[1]))
    source_rest = {role: source_armature.data.bones[name].matrix_local.copy() for role, name in source_roles.items() if name in source_armature.data.bones}
    missing_source = sorted(source_roles[role] for role in ROLE_ORDER if source_roles[role] not in source_armature.pose.bones)
    if missing_source:
        raise RuntimeError(f"source semantic bones unavailable: {missing_source}")
    source_height = skeleton_height(source_armature)
    samples = []
    for frame in range(source_start, source_end + 1):
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        samples.append({
            role: source_armature.pose.bones[source_roles[role]].matrix.copy()
            for role in ROLE_ORDER
        })

    target_armature = import_single_armature(target)
    target_meshes = [
        obj for obj in bpy.context.scene.objects
        if obj.type == "MESH" and any(mod.type == "ARMATURE" and mod.object == target_armature for mod in obj.modifiers)
    ]
    missing_target = sorted(target_roles[role] for role in ROLE_ORDER if target_roles[role] not in target_armature.pose.bones)
    if missing_target or not target_meshes:
        raise RuntimeError(f"target mapping unavailable: bones={missing_target}, meshes={len(target_meshes)}")
    target_rest = {role: target_armature.data.bones[target_roles[role]].matrix_local.copy() for role in ROLE_ORDER}
    target_height = skeleton_height(target_armature)
    translation_scale = target_height / source_height

    for obj in bpy.context.scene.objects:
        if obj.animation_data:
            obj.animation_data_clear()
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)
    action = bpy.data.actions.new(f"AS_{target_id}_ActiveIdle_{iteration}")
    target_armature.animation_data_create()
    target_armature.animation_data.action = action

    applied_roles = UPPER_BODY_ROLES if upper_body_only else ROLE_ORDER
    for target_frame, source_sample in enumerate(samples, start=1):
        for pose_bone in target_armature.pose.bones:
            pose_bone.matrix_basis = Matrix.Identity(4)
        bpy.context.view_layer.update()
        for role in applied_roles:
            source_matrix = source_sample[role]
            source_rest_matrix = source_rest[role]
            target_bone = target_armature.pose.bones[target_roles[role]]
            current = target_bone.matrix.copy()
            global_delta = source_matrix.to_quaternion() @ source_rest_matrix.to_quaternion().inverted()
            desired_rotation = global_delta @ target_rest[role].to_quaternion()
            correction = rest_corrections.get(role)
            if correction:
                axes = {"X": Vector((1.0, 0.0, 0.0)), "Y": Vector((0.0, 1.0, 0.0)), "Z": Vector((0.0, 0.0, 1.0))}
                axis = axes.get(correction["axis"])
                if axis is None:
                    raise RuntimeError(f"unsupported correction axis: {correction}")
                desired_rotation = Quaternion(axis, math.radians(float(correction["degrees"]))) @ desired_rotation
            desired = desired_rotation.to_matrix().to_4x4()
            desired.translation = current.translation
            if role == "pelvis":
                source_offset = source_matrix.translation - source_rest_matrix.translation
                desired.translation += source_offset * translation_scale * pelvis_translation_factor
            target_bone.matrix = desired
            target_bone.rotation_mode = "QUATERNION"
            target_bone.keyframe_insert("location", frame=target_frame, group=target_bone.name)
            target_bone.keyframe_insert("rotation_quaternion", frame=target_frame, group=target_bone.name)
            target_bone.keyframe_insert("scale", frame=target_frame, group=target_bone.name)
            bpy.context.view_layer.update()

    scene = bpy.context.scene
    scene.render.fps = 24
    scene.frame_start = 1
    scene.frame_end = len(samples)
    bpy.ops.object.select_all(action="DESELECT")
    target_armature.select_set(True)
    for mesh in target_meshes:
        mesh.select_set(True)
    bpy.context.view_layer.objects.active = target_armature
    output.parent.mkdir(parents=True, exist_ok=True)
    result = bpy.ops.export_scene.fbx(
        filepath=str(output.resolve()),
        use_selection=True,
        object_types={"ARMATURE", "MESH"},
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_ALL",
        axis_forward="-Y",
        axis_up="Z",
        add_leaf_bones=False,
        use_armature_deform_only=False,
        bake_anim=True,
        bake_anim_use_all_bones=True,
        bake_anim_use_nla_strips=False,
        bake_anim_use_all_actions=False,
        bake_anim_step=1.0,
        bake_anim_simplify_factor=0.0,
        path_mode="STRIP",
        embed_textures=False,
    )
    if "FINISHED" not in result or not output.is_file() or output.stat().st_size < 1024:
        raise RuntimeError(f"retarget export failed: {result}")

    report = {
        "schemaVersion": 1,
        "iteration": iteration,
        "status": "authored-draft-semantic-idle-retarget",
        "targetId": target_id,
        "sources": {
            "motion": {"file": str(motion.resolve()), "sha256": hashlib.sha256(motion.read_bytes()).hexdigest()},
            "target": {"file": str(target.resolve()), "sha256": hashlib.sha256(target.read_bytes()).hexdigest()},
            "profiles": {"file": str(profiles_path.resolve()), "sha256": hashlib.sha256(profiles_path.read_bytes()).hexdigest()},
        },
        "output": {"file": str(output.resolve()), "sha256": hashlib.sha256(output.read_bytes()).hexdigest()},
        "fps": 24,
        "frameRange": [1, len(samples)],
        "mappedRoleCount": len(applied_roles),
        "appliedRoles": list(applied_roles),
        "upperBodyOnly": upper_body_only,
        "globalRestPoseCorrections": rest_corrections,
        "translationScale": translation_scale,
        "pelvisTranslationFactor": pelvis_translation_factor,
        "hypothesis": "Rest-orientation-corrected global rotations preserve active-idle intent across different humanoid bone axes.",
        "visualValidationPending": True,
        "humanApproved": False,
        "releaseEligible": False,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    args = parse_args()
    report = retarget_semantic_idle_v529(
        args.motion, args.target, args.profiles, args.target_id,
        args.output, args.report, args.iteration, args.pelvis_translation_factor,
        args.upper_body_only,
    )
    print(json.dumps({"iteration": report["iteration"], "frames": report["frameRange"][-1]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
