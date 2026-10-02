#!/usr/bin/env python3
"""Author a visually conservative Hayley jawOpen facial calibration clip."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy


OPEN_DRIVERS = {
    "cJaw": {"rotationEulerDegrees": [5.0, 0.0, 0.0], "locationCm": [0.0, 0.0, 0.0]},
    "cTeethLower": {"rotationEulerDegrees": [0.0, 0.0, 0.0], "locationCm": [0.0, -0.55, -0.18]},
    "cLipLower": {"rotationEulerDegrees": [0.0, 0.0, 0.0], "locationCm": [0.0, -0.38, -0.08]},
    "lLipLower": {"rotationEulerDegrees": [0.0, 0.0, 0.0], "locationCm": [0.0, -0.26, -0.05]},
    "rLipLower": {"rotationEulerDegrees": [0.0, 0.0, 0.0], "locationCm": [0.0, -0.26, -0.05]},
    "lLipLowerOuter": {"rotationEulerDegrees": [0.0, 0.0, 0.0], "locationCm": [0.0, -0.14, -0.02]},
    "rLipLowerOuter": {"rotationEulerDegrees": [0.0, 0.0, 0.0], "locationCm": [0.0, -0.14, -0.02]},
}
POSES = ((1, "neutral", 0.0), (16, "conservative_open", 1.0), (31, "neutral_return", 0.0))


def build_compound_jawopen_v419(source):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(source))
    armatures = [item for item in bpy.context.scene.objects if item.type == "ARMATURE"]
    if len(armatures) != 1:
        raise RuntimeError(f"expected one Hayley armature, found {len(armatures)}")
    armature = armatures[0]
    missing = sorted(set(OPEN_DRIVERS) - set(armature.pose.bones.keys()))
    if missing:
        raise RuntimeError(f"missing lower-face bones: {missing}")
    armature.animation_data_clear()
    for bone in armature.pose.bones:
        bone.location = (0.0, 0.0, 0.0)
        bone.rotation_mode = "QUATERNION"
        bone.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        bone.scale = (1.0, 1.0, 1.0)
    action = bpy.data.actions.new("AS_Hayley_CompoundJawOpen_v419")
    armature.animation_data_create()
    armature.animation_data.action = action
    for frame, _, weight in POSES:
        for name, driver in OPEN_DRIVERS.items():
            bone = armature.pose.bones[name]
            bone.rotation_mode = "XYZ"
            bone.rotation_euler = tuple(math.radians(value * weight) for value in driver["rotationEulerDegrees"])
            bone.location = tuple(value * weight for value in driver["locationCm"])
            bone.keyframe_insert(data_path="rotation_euler", frame=frame, group=name)
            bone.keyframe_insert(data_path="location", frame=frame, group=name)
    bpy.context.scene.render.fps = 30
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = 31
    return armature, action


def export_compound_jawopen_v419(output, armature):
    if output.exists():
        raise FileExistsError(f"refusing to overwrite v419 FBX: {output}")
    meshes = [
        item for item in bpy.context.scene.objects
        if item.type == "MESH"
        and any(mod.type == "ARMATURE" and mod.object == armature for mod in item.modifiers)
    ]
    if not meshes:
        raise RuntimeError("jawOpen export has no skinned meshes")
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
    args = parser.parse_args(values)
    if args.report.exists() or args.output.exists():
        raise FileExistsError("refusing to overwrite immutable v419 outputs")
    armature, action = build_compound_jawopen_v419(args.input)
    meshes = export_compound_jawopen_v419(args.output, armature)
    report = {
        "schemaVersion": 1,
        "iteration": "v419",
        "status": "authored-draft-conservative-jawopen",
        "source": str(args.input.resolve()),
        "output": str(args.output.resolve()),
        "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
        "action": action.name,
        "drivers": OPEN_DRIVERS,
        "poses": [{"frame": frame, "label": label, "weight": weight} for frame, label, weight in POSES],
        "meshCount": len(meshes),
        "hypothesis": "Limit cJaw to five degrees and let the lower lip and teeth create the opening without elongating the chin.",
        "rejectedPredecessor": "v411: visible chin elongation in material-independent QA",
        "visualValidationPending": True,
        "humanApproved": False,
        "releaseEligible": False,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
