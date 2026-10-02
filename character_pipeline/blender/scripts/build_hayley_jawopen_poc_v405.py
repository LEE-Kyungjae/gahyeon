#!/usr/bin/env python3
"""Author a conservative Hayley jawOpen proof animation with skinned geometry."""

import argparse
import json
import math
from pathlib import Path
import sys

import bpy


POSES = (
    (1, "neutral", 0.0),
    (16, "jaw_open", 18.0),
    (31, "neutral_return", 0.0),
)


def build_hayley_jawopen_poc_v405(source):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(source))
    armatures = [item for item in bpy.context.scene.objects if item.type == "ARMATURE"]
    if len(armatures) != 1:
        raise RuntimeError(f"expected one Hayley armature, found {len(armatures)}")
    armature = armatures[0]
    jaw = armature.pose.bones.get("cJaw")
    if jaw is None:
        raise RuntimeError("Hayley cJaw bone is unavailable")
    armature.animation_data_clear()
    for bone in armature.pose.bones:
        bone.location = (0.0, 0.0, 0.0)
        bone.rotation_mode = "QUATERNION"
        bone.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        bone.scale = (1.0, 1.0, 1.0)
    action = bpy.data.actions.new("AS_Hayley_JawOpen_v405")
    armature.animation_data_create()
    armature.animation_data.action = action
    jaw.rotation_mode = "XYZ"
    for frame, _, angle in POSES:
        jaw.rotation_euler = (math.radians(angle), 0.0, 0.0)
        jaw.keyframe_insert(data_path="rotation_euler", frame=frame, group="cJaw")
    bpy.context.scene.render.fps = 30
    bpy.context.scene.frame_start = POSES[0][0]
    bpy.context.scene.frame_end = POSES[-1][0]
    return armature, action


def export_hayley_jawopen_poc_v405(output, armature):
    if output.exists():
        raise FileExistsError(f"refusing to overwrite v405 FBX: {output}")
    meshes = [
        item for item in bpy.context.scene.objects
        if item.type == "MESH"
        and any(mod.type == "ARMATURE" and mod.object == armature for mod in item.modifiers)
    ]
    if not meshes:
        raise RuntimeError("Hayley jawOpen export has no skinned meshes")
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for item in (armature, *meshes):
        item.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.export_scene.fbx(
        filepath=str(output),
        use_selection=True,
        object_types={"ARMATURE", "MESH"},
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_ALL",
        add_leaf_bones=False,
        use_armature_deform_only=False,
        bake_anim=True,
        bake_anim_use_all_bones=True,
        bake_anim_use_nla_strips=False,
        bake_anim_use_all_actions=False,
        bake_anim_force_startend_keying=True,
        bake_anim_step=1.0,
        bake_anim_simplify_factor=0.0,
        path_mode="STRIP",
        embed_textures=False,
    )
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError("Hayley jawOpen FBX export failed")
    return meshes


def main():
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(values)
    if not args.input.is_file():
        raise FileNotFoundError(args.input)
    if args.report.exists():
        raise FileExistsError(f"refusing to overwrite v405 report: {args.report}")
    armature, action = build_hayley_jawopen_poc_v405(args.input)
    meshes = export_hayley_jawopen_poc_v405(args.output, armature)
    report = {
        "schemaVersion": 1,
        "iteration": "v405",
        "status": "authored-draft-isolated-jawopen",
        "source": str(args.input.resolve()),
        "output": str(args.output.resolve()),
        "action": action.name,
        "targetBone": "cJaw",
        "targetAxis": "local-positive-x",
        "maximumDegrees": 18.0,
        "fps": 30,
        "meshCount": len(meshes),
        "poses": [
            {"frame": frame, "label": label, "degrees": angle}
            for frame, label, angle in POSES
        ],
        "lowerLipAndTeethCompensation": "not-yet-calibrated",
        "humanApproved": False,
        "releaseEligible": False,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
