#!/usr/bin/env python3
"""Bake natural Hayley body idle plus CuteGirl-timed native facial motion."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy


BODY_FPS = 24.0
FACE_FPS = 30.0
TARGET_FPS = 30
DURATION_SECONDS = 10.125
TARGET_END = round(DURATION_SECONDS * TARGET_FPS) + 1
FACE_BONES = {
    "cJaw", "lEye", "rEye", "lLipCorner", "rLipCorner", "lCheekInner", "rCheekInner",
    "lEyelidUpperA", "lEyelidUpperB", "lEyelidLowerA", "lEyelidLowerB",
    "rEyelidUpperA", "rEyelidUpperB", "rEyelidLowerA", "rEyelidLowerB",
}


def parse_args():
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--body", type=Path, required=True)
    parser.add_argument("--face", type=Path, required=True)
    parser.add_argument("--clean", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args(values)


def transform_record(bone):
    return (
        tuple(float(value) for value in bone.location),
        tuple(float(value) for value in bone.rotation_quaternion),
        tuple(float(value) for value in bone.scale),
    )


def set_fractional_frame(value):
    integer = math.floor(value)
    bpy.context.scene.frame_set(integer, subframe=value - integer)


def sample_animation(path: Path, fps: float, start_frame: float, bone_filter=None):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path))
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    if len(armatures) != 1:
        raise RuntimeError(f"expected one armature in {path}, found {len(armatures)}")
    armature = armatures[0]
    names = sorted(set(armature.pose.bones.keys()) & set(bone_filter)) if bone_filter else sorted(armature.pose.bones.keys())
    samples = []
    for target_frame in range(1, TARGET_END + 1):
        seconds = (target_frame - 1) / TARGET_FPS
        set_fractional_frame(start_frame + seconds * fps)
        samples.append({name: transform_record(armature.pose.bones[name]) for name in names})
    return samples, names


def changed_bones(samples, names, tolerance=1e-5):
    changed = []
    for name in names:
        baseline = samples[0][name]
        if any(
            max(abs(value - base) for current, initial in zip(sample[name], baseline) for value, base in zip(current, initial)) > tolerance
            for sample in samples[1:]
        ):
            changed.append(name)
    return changed


def apply_transform(bone, transform, frame):
    location, quaternion, scale = transform
    bone.location = location
    bone.rotation_mode = "QUATERNION"
    bone.rotation_quaternion = quaternion
    bone.scale = scale
    bone.keyframe_insert("location", frame=frame, group=bone.name)
    bone.keyframe_insert("rotation_quaternion", frame=frame, group=bone.name)
    bone.keyframe_insert("scale", frame=frame, group=bone.name)


def build_hayley_living_idle_v509(body, face, clean, output, report_path):
    for source in (body, face, clean):
        if not source.is_file():
            raise FileNotFoundError(source)
    for destination in (output, report_path):
        if destination.exists():
            raise FileExistsError(f"refusing to overwrite immutable v509 output: {destination}")
    body_samples, body_names = sample_animation(body, BODY_FPS, 1.0)
    face_samples, face_names = sample_animation(face, FACE_FPS, 2.0, FACE_BONES)
    body_changed = changed_bones(body_samples, body_names)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(clean))
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    if len(armatures) != 1:
        raise RuntimeError(f"expected one clean Hayley armature, found {len(armatures)}")
    armature = armatures[0]
    missing_body = sorted(set(body_changed) - set(armature.pose.bones.keys()))
    missing_face = sorted(set(face_names) - set(armature.pose.bones.keys()))
    if missing_body or missing_face:
        raise RuntimeError(f"clean skeleton mismatch: body={missing_body}, face={missing_face}")
    for obj in bpy.context.scene.objects:
        if obj.animation_data:
            obj.animation_data_clear()
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)
    action = bpy.data.actions.new("AS_Hayley_LivingIdle_v509")
    armature.animation_data_create()
    armature.animation_data.action = action
    for index, target_frame in enumerate(range(1, TARGET_END + 1)):
        for name in body_changed:
            if name not in FACE_BONES:
                apply_transform(armature.pose.bones[name], body_samples[index][name], target_frame)
        for name in face_names:
            apply_transform(armature.pose.bones[name], face_samples[index][name], target_frame)
        root = armature.pose.bones.get("root")
        if root:
            root.location = (0.0, 0.0, 0.0)
            root.rotation_mode = "QUATERNION"
            root.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
            root.scale = (1.0, 1.0, 1.0)
            root.keyframe_insert("location", frame=target_frame, group="root")
            root.keyframe_insert("rotation_quaternion", frame=target_frame, group="root")
            root.keyframe_insert("scale", frame=target_frame, group="root")

    scene = bpy.context.scene
    scene.render.fps = TARGET_FPS
    scene.frame_start = 1
    scene.frame_end = TARGET_END
    meshes = [
        obj for obj in bpy.context.scene.objects if obj.type == "MESH"
        and any(mod.type == "ARMATURE" and mod.object == armature for mod in obj.modifiers)
    ]
    bpy.ops.object.select_all(action="DESELECT")
    for obj in [armature, *meshes]:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = armature
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.fbx(
        filepath=str(output), use_selection=True, object_types={"ARMATURE", "MESH"},
        apply_unit_scale=True, apply_scale_options="FBX_SCALE_ALL", add_leaf_bones=False,
        use_armature_deform_only=False, bake_anim=True, bake_anim_use_all_bones=True,
        bake_anim_use_nla_strips=False, bake_anim_use_all_actions=False,
        bake_anim_step=1.0, bake_anim_simplify_factor=0.0, path_mode="STRIP", embed_textures=False,
    )
    report = {
        "schemaVersion": 1, "iteration": "v509", "status": "authored-draft-living-idle",
        "sources": {
            "body": {"file": str(body.resolve()), "sha256": hashlib.sha256(body.read_bytes()).hexdigest()},
            "face": {"file": str(face.resolve()), "sha256": hashlib.sha256(face.read_bytes()).hexdigest()},
            "clean": {"file": str(clean.resolve()), "sha256": hashlib.sha256(clean.read_bytes()).hexdigest()},
        },
        "output": str(output.resolve()), "outputSha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "durationSeconds": DURATION_SECONDS, "fps": TARGET_FPS, "frameRange": [1, TARGET_END],
        "bodyAnimatedBoneCount": len(body_changed), "faceBoneCount": len(face_names),
        "faceBones": face_names,
        "hypothesis": "Natural-arm active idle plus donor-timed native facial bones will read alive without returning Hayley to an A-pose.",
        "humanApproved": False, "releaseEligible": False,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    args = parse_args()
    report = build_hayley_living_idle_v509(args.body, args.face, args.clean, args.output, args.report)
    print(json.dumps({"iteration": report["iteration"], "bodyAnimatedBoneCount": report["bodyAnimatedBoneCount"], "faceBoneCount": report["faceBoneCount"]}))


if __name__ == "__main__":
    main()
