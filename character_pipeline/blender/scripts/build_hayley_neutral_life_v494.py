#!/usr/bin/env python3
"""Author a restrained neutral life loop on Hayley's verified clean skeleton."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy


FPS = 30
START = 1
END = 301
BLINK_DELTAS = {
    "lEyelidUpperA": (0.0, -0.42, 0.0), "lEyelidUpperB": (0.0, -0.32, 0.0),
    "rEyelidUpperA": (0.0, -0.42, 0.0), "rEyelidUpperB": (0.0, -0.32, 0.0),
    "lEyelidLowerA": (0.0, 0.13, 0.0), "lEyelidLowerB": (0.0, 0.10, 0.0),
    "rEyelidLowerA": (0.0, 0.13, 0.0), "rEyelidLowerB": (0.0, 0.10, 0.0),
}


def parse_args() -> argparse.Namespace:
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    return parser.parse_args(values)


def add_location_key(bone, frame: int, delta: tuple[float, float, float]) -> None:
    bone.location = delta
    bone.keyframe_insert("location", frame=frame, group=bone.name)


def add_rotation_key(bone, frame: int, degrees: tuple[float, float, float]) -> None:
    bone.rotation_mode = "XYZ"
    bone.rotation_euler = tuple(math.radians(value) for value in degrees)
    bone.keyframe_insert("rotation_euler", frame=frame, group=bone.name)


def action_fcurves(action) -> list:
    curves = list(getattr(action, "fcurves", ()))
    for layer in getattr(action, "layers", ()):
        for strip in getattr(layer, "strips", ()):
            for bag in getattr(strip, "channelbags", ()):
                curves.extend(getattr(bag, "fcurves", ()))
    return curves


def build_hayley_neutral_life_v494(source: Path, output: Path, report_path: Path) -> dict[str, object]:
    if not source.is_file():
        raise FileNotFoundError(source)
    for destination in (output, report_path):
        if destination.exists():
            raise FileExistsError(f"refusing to overwrite immutable v494 output: {destination}")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(source))
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    if len(armatures) != 1:
        raise RuntimeError(f"expected one armature, found {[obj.name for obj in armatures]}")
    armature = armatures[0]
    required = {"pelvis", "spine2", "chest", "neck", "head", "lEye", "rEye", *BLINK_DELTAS}
    missing = sorted(required - set(armature.pose.bones.keys()))
    if missing:
        raise RuntimeError(f"Hayley life-loop bones missing: {missing}")
    for obj in bpy.context.scene.objects:
        if obj.animation_data:
            obj.animation_data_clear()
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)
    armature.animation_data_create()
    action = bpy.data.actions.new("AS_Hayley_NeutralLife_v494")
    armature.animation_data.action = action
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.frame_start = START
    scene.frame_end = END

    # Irregular, low-amplitude breathing. Local rotations stay below one degree.
    breathing = ((1, 0.0), (43, 0.65), (88, -0.18), (137, 0.78), (187, -0.12), (236, 0.58), (301, 0.0))
    for frame, value in breathing:
        add_rotation_key(armature.pose.bones["chest"], frame, (value, 0.0, 0.0))
        add_rotation_key(armature.pose.bones["spine2"], frame, (value * 0.35, 0.0, 0.0))

    # Slow weight transfer and non-synchronous head/neck response.
    for frame, x_cm, roll in ((1, 0.0, 0.0), (78, 0.20, 0.45), (154, -0.12, -0.35), (231, 0.16, 0.3), (301, 0.0, 0.0)):
        add_location_key(armature.pose.bones["pelvis"], frame, (x_cm, 0.0, 0.0))
        add_rotation_key(armature.pose.bones["pelvis"], frame, (0.0, 0.0, roll))
    for frame, pitch, yaw, roll in (
        (1, 0.0, 0.0, 0.0), (62, -0.5, 1.6, 0.35), (119, 0.25, -1.1, -0.2),
        (194, -0.25, 1.0, 0.25), (256, 0.35, -0.7, -0.15), (301, 0.0, 0.0, 0.0),
    ):
        add_rotation_key(armature.pose.bones["head"], frame, (pitch, yaw, roll))
        add_rotation_key(armature.pose.bones["neck"], frame, (pitch * 0.35, yaw * 0.3, roll * 0.3))

    # Small gaze changes lead the head and return to center before loop closure.
    for frame, pitch, yaw in ((1, 0.0, 0.0), (52, -0.5, 1.8), (106, 0.2, -1.3), (184, -0.3, 1.1), (247, 0.25, -0.8), (301, 0.0, 0.0)):
        for name in ("lEye", "rEye"):
            add_rotation_key(armature.pose.bones[name], frame, (pitch, yaw, 0.0))

    # Non-periodic blink spacing, including a short double blink near the end.
    blink_centers = (71, 169, 247, 257)
    for name, delta in BLINK_DELTAS.items():
        bone = armature.pose.bones[name]
        for center in blink_centers:
            add_location_key(bone, center - 3, (0.0, 0.0, 0.0))
            add_location_key(bone, center, delta)
            add_location_key(bone, center + 3, (0.0, 0.0, 0.0))
        add_location_key(bone, START, (0.0, 0.0, 0.0))
        add_location_key(bone, END, (0.0, 0.0, 0.0))

    for curve in action_fcurves(action):
        for point in curve.keyframe_points:
            point.interpolation = "BEZIER"
    scene.frame_set(START)
    bpy.context.view_layer.update()
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
        bake_anim_step=1.0, bake_anim_simplify_factor=0.0, path_mode="COPY", embed_textures=False,
    )
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError("v494 life-loop export failed")
    report = {
        "schemaVersion": 1, "iteration": "v494", "status": "authored-draft-neutral-life-loop",
        "source": str(source.resolve()), "sourceSha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "output": str(output.resolve()), "outputSha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "fps": FPS, "frameRange": [START, END], "durationSeconds": (END - START) / FPS,
        "blinkCenters": list(blink_centers), "breathingKeys": [frame for frame, _ in breathing],
        "hypothesis": "Low-amplitude asynchronous breathing, gaze, head, weight, and blink motion will read as alive without competing with speech gestures.",
        "humanApproved": False, "releaseEligible": False,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> int:
    args = parse_args()
    report = build_hayley_neutral_life_v494(args.input, args.output, args.report)
    print(json.dumps({"iteration": report["iteration"], "durationSeconds": report["durationSeconds"], "blinkCenters": report["blinkCenters"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
