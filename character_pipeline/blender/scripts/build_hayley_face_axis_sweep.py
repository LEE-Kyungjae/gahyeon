#!/usr/bin/env python3
"""Build an animation-only FBX that sweeps Hayley's jaw across local axes."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

import bpy


POSES = (
    (1, "neutral", (0.0, 0.0, 0.0)),
    (10, "jaw_x_plus_5", (5.0, 0.0, 0.0)),
    (20, "jaw_x_minus_5", (-5.0, 0.0, 0.0)),
    (30, "jaw_y_plus_5", (0.0, 5.0, 0.0)),
    (40, "jaw_y_minus_5", (0.0, -5.0, 0.0)),
    (50, "jaw_z_plus_5", (0.0, 0.0, 5.0)),
    (60, "jaw_z_minus_5", (0.0, 0.0, -5.0)),
)


def parse_args():
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args(values)


def build_hayley_face_axis_sweep(source):
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
    action = bpy.data.actions.new("AS_Hayley_JawAxisSweep_v388")
    armature.animation_data_create()
    armature.animation_data.action = action
    jaw.rotation_mode = "XYZ"
    for frame, _, degrees in POSES:
        jaw.rotation_euler = tuple(math.radians(value) for value in degrees)
        jaw.keyframe_insert(data_path="rotation_euler", frame=frame, group="cJaw")
    bpy.context.scene.render.fps = 30
    bpy.context.scene.frame_start = POSES[0][0]
    bpy.context.scene.frame_end = POSES[-1][0]
    return armature, action


def export_hayley_face_sweep_animation(output, armature):
    if output.exists():
        raise FileExistsError(f"refusing to overwrite animation FBX: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.export_scene.fbx(
        filepath=str(output),
        use_selection=True,
        object_types={"ARMATURE"},
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
    )
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError("jaw-axis animation export failed")


def main():
    args = parse_args()
    if not args.input.is_file():
        raise FileNotFoundError(args.input)
    if args.report.exists():
        raise FileExistsError(f"refusing to overwrite report: {args.report}")
    armature, action = build_hayley_face_axis_sweep(args.input)
    export_hayley_face_sweep_animation(args.output, armature)
    report = {
        "schemaVersion": 1,
        "iteration": "v388",
        "status": "authored-draft-jaw-axis-sweep",
        "source": str(args.input.resolve()),
        "output": str(args.output.resolve()),
        "action": action.name,
        "fps": 30,
        "poses": [
            {"frame": frame, "label": label, "localEulerDegrees": degrees}
            for frame, label, degrees in POSES
        ],
        "purpose": "Select the real jaw-open axis and safe range from Unreal renders before donor curve mapping.",
        "humanApproved": False,
        "releaseEligible": False,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
