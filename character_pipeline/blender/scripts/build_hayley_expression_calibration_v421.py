#!/usr/bin/env python3
"""Build immutable Hayley blink and smile calibration poses."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy


POSES = (
    (1, "neutral", {}),
    (11, "blink", {
        "lEyelidUpperA": (0.0, -0.42, 0.0), "lEyelidUpperB": (0.0, -0.32, 0.0),
        "rEyelidUpperA": (0.0, -0.42, 0.0), "rEyelidUpperB": (0.0, -0.32, 0.0),
        "lEyelidLowerA": (0.0, 0.13, 0.0), "lEyelidLowerB": (0.0, 0.10, 0.0),
        "rEyelidLowerA": (0.0, 0.13, 0.0), "rEyelidLowerB": (0.0, 0.10, 0.0),
    }),
    (21, "neutral_after_blink", {}),
    (31, "smile", {
        "lLipCorner": (0.20, 0.28, 0.0), "rLipCorner": (-0.20, 0.28, 0.0),
        "lCheekInner": (0.0, 0.10, 0.0), "rCheekInner": (0.0, 0.10, 0.0),
    }),
    (41, "neutral_return", {}),
)


def build_hayley_expression_calibration_v421(source, iteration="v421"):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(source))
    armatures = [item for item in bpy.context.scene.objects if item.type == "ARMATURE"]
    if len(armatures) != 1:
        raise RuntimeError(f"expected one Hayley armature, found {len(armatures)}")
    armature = armatures[0]
    required = {name for _, _, values in POSES for name in values}
    missing = sorted(required - set(armature.pose.bones.keys()))
    if missing:
        raise RuntimeError(f"missing facial bones: {missing}")
    armature.animation_data_clear()
    for bone in armature.pose.bones:
        bone.location = (0.0, 0.0, 0.0)
        bone.rotation_mode = "QUATERNION"
        bone.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        bone.scale = (1.0, 1.0, 1.0)
    action = bpy.data.actions.new(f"AS_Hayley_ExpressionCalibration_{iteration}")
    armature.animation_data_create()
    armature.animation_data.action = action
    for frame, _, values in POSES:
        for name in required:
            bone = armature.pose.bones[name]
            bone.location = values.get(name, (0.0, 0.0, 0.0))
            bone.keyframe_insert(data_path="location", frame=frame, group=name)
    bpy.context.scene.render.fps = 30
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = 41
    return armature, action


def export_v421(output, armature):
    if output.exists():
        raise FileExistsError(f"refusing to overwrite v421 FBX: {output}")
    meshes = [
        item for item in bpy.context.scene.objects
        if item.type == "MESH"
        and any(mod.type == "ARMATURE" and mod.object == armature for mod in item.modifiers)
    ]
    if not meshes:
        raise RuntimeError("facial calibration export has no skinned meshes")
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for item in (armature, *meshes):
        item.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.export_scene.fbx(
        filepath=str(output), use_selection=True, object_types={"ARMATURE", "MESH"},
        apply_unit_scale=True, apply_scale_options="FBX_SCALE_ALL", add_leaf_bones=False,
        use_armature_deform_only=False, bake_anim=True, bake_anim_use_all_bones=True,
        bake_anim_use_nla_strips=False, bake_anim_use_all_actions=False,
        bake_anim_force_startend_keying=True, bake_anim_step=1.0,
        bake_anim_simplify_factor=0.0, path_mode="STRIP", embed_textures=False,
    )
    return meshes


def main():
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--iteration", default="v421")
    args = parser.parse_args(values)
    if args.report.exists() or args.output.exists():
        raise FileExistsError("refusing to overwrite immutable v421 outputs")
    armature, action = build_hayley_expression_calibration_v421(args.input, args.iteration)
    meshes = export_v421(args.output, armature)
    report = {
        "schemaVersion": 1, "iteration": args.iteration,
        "status": "authored-draft-blink-smile-calibration",
        "source": str(args.input.resolve()), "output": str(args.output.resolve()),
        "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
        "action": action.name, "meshCount": len(meshes),
        "poses": [{"frame": frame, "label": label, "locationsCm": values} for frame, label, values in POSES],
        "hypotheses": {
            "blink": "Upper lids translate down and lower lids rise along each eyelid bone local Y axis.",
            "smile": "Lip corners widen and rise while inner cheeks rise slightly.",
        },
        "visualValidationPending": True, "humanApproved": False, "releaseEligible": False,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
