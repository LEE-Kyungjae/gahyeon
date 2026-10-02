#!/usr/bin/env python3
"""Project CuteGirl expression timing onto Hayley's native facial bones."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy


SOURCE_FPS = 60
TARGET_FPS = 30
SOURCE_START = 1
SOURCE_END = 785
BLINK_BONES = {
    "L": {"lEyelidUpperA": (0.0, -0.42, 0.0), "lEyelidUpperB": (0.0, -0.32, 0.0),
          "lEyelidLowerA": (0.0, 0.13, 0.0), "lEyelidLowerB": (0.0, 0.10, 0.0)},
    "R": {"rEyelidUpperA": (0.0, -0.42, 0.0), "rEyelidUpperB": (0.0, -0.32, 0.0),
          "rEyelidLowerA": (0.0, 0.13, 0.0), "rEyelidLowerB": (0.0, 0.10, 0.0)},
}


def parse_args():
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--donor", type=Path, required=True)
    parser.add_argument("--hayley", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args(values)


def clamp(value, low=0.0, high=1.0):
    return max(low, min(high, value))


def sample_donor(source: Path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(source))
    body = bpy.data.objects.get("CC_Base_Body")
    if body is None or body.data.shape_keys is None:
        raise RuntimeError("CuteGirl body shape-key mesh is unavailable")
    keys = body.data.shape_keys.key_blocks
    required = {
        "Eye_Blink_L", "Eye_Blink_R", "Eye_L_Look_L", "Eye_R_Look_L",
        "Eye_L_Look_R", "Eye_R_Look_R", "Eye_L_Look_Up", "Eye_R_Look_Up",
        "Eye_L_Look_Down", "Eye_R_Look_Down", "Mouth_Smile_L", "Mouth_Smile_R", "Jaw_Open",
    }
    missing = sorted(required - set(keys.keys()))
    if missing:
        raise RuntimeError(f"CuteGirl semantic channels missing: {missing}")
    samples = []
    for source_frame in range(SOURCE_START, SOURCE_END + 1, 2):
        bpy.context.scene.frame_set(source_frame)
        samples.append({name: float(keys[name].value) for name in required} | {"sourceFrame": source_frame})
    return samples


def key_location(bone, frame, value):
    bone.location = value
    bone.keyframe_insert("location", frame=frame, group=bone.name)


def key_rotation(bone, frame, degrees):
    bone.rotation_mode = "XYZ"
    bone.rotation_euler = tuple(math.radians(value) for value in degrees)
    bone.keyframe_insert("rotation_euler", frame=frame, group=bone.name)


def build_hayley_cutegirl_face_performance_v503(donor, hayley, output, report_path):
    for path in (donor, hayley):
        if not path.is_file():
            raise FileNotFoundError(path)
    for destination in (output, report_path):
        if destination.exists():
            raise FileExistsError(f"refusing to overwrite immutable v503 output: {destination}")
    samples = sample_donor(donor)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(hayley))
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    if len(armatures) != 1:
        raise RuntimeError(f"expected one Hayley armature, found {len(armatures)}")
    armature = armatures[0]
    required_bones = {
        "lEye", "rEye", "lLipCorner", "rLipCorner", "lCheekInner", "rCheekInner", "cJaw",
        *(name for side in BLINK_BONES.values() for name in side),
    }
    missing = sorted(required_bones - set(armature.pose.bones.keys()))
    if missing:
        raise RuntimeError(f"Hayley face bones missing: {missing}")
    for obj in bpy.context.scene.objects:
        if obj.animation_data:
            obj.animation_data_clear()
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)
    action = bpy.data.actions.new("AS_Hayley_CuteGirlFaceTiming_v503")
    armature.animation_data_create()
    armature.animation_data.action = action

    for target_frame, sample in enumerate(samples, 1):
        blink_l = clamp(sample["Eye_Blink_L"])
        blink_r = clamp(sample["Eye_Blink_R"])
        for name, delta in BLINK_BONES["L"].items():
            key_location(armature.pose.bones[name], target_frame, tuple(value * blink_l for value in delta))
        for name, delta in BLINK_BONES["R"].items():
            key_location(armature.pose.bones[name], target_frame, tuple(value * blink_r for value in delta))

        look_left = (sample["Eye_L_Look_L"] + sample["Eye_R_Look_L"]) * 0.5
        look_right = (sample["Eye_L_Look_R"] + sample["Eye_R_Look_R"]) * 0.5
        look_up = (sample["Eye_L_Look_Up"] + sample["Eye_R_Look_Up"]) * 0.5
        look_down = (sample["Eye_L_Look_Down"] + sample["Eye_R_Look_Down"]) * 0.5
        pitch = clamp(look_down - look_up, -1.0, 1.0) * 4.0
        yaw = clamp(look_right - look_left, -1.0, 1.0) * 5.0
        for name in ("lEye", "rEye"):
            key_rotation(armature.pose.bones[name], target_frame, (pitch, yaw, 0.0))

        smile_l = clamp(sample["Mouth_Smile_L"] / 0.27)
        smile_r = clamp(sample["Mouth_Smile_R"] / 0.27)
        key_location(armature.pose.bones["lLipCorner"], target_frame, (0.08 * smile_l, 0.11 * smile_l, 0.0))
        key_location(armature.pose.bones["rLipCorner"], target_frame, (-0.08 * smile_r, 0.11 * smile_r, 0.0))
        key_location(armature.pose.bones["lCheekInner"], target_frame, (0.0, 0.04 * smile_l, 0.0))
        key_location(armature.pose.bones["rCheekInner"], target_frame, (0.0, 0.04 * smile_r, 0.0))
        jaw = clamp(sample["Jaw_Open"] / 0.12)
        key_rotation(armature.pose.bones["cJaw"], target_frame, (2.0 * jaw, 0.0, 0.0))

    scene = bpy.context.scene
    scene.render.fps = TARGET_FPS
    scene.frame_start = 1
    scene.frame_end = len(samples)
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
        use_armature_deform_only=False, bake_anim=True, bake_anim_use_all_bones=False,
        bake_anim_use_nla_strips=False, bake_anim_use_all_actions=False,
        bake_anim_step=1.0, bake_anim_simplify_factor=0.0, path_mode="STRIP", embed_textures=False,
    )
    report = {
        "schemaVersion": 1, "iteration": "v503", "status": "authored-draft-face-timing-transfer",
        "donor": str(donor.resolve()), "donorSha256": hashlib.sha256(donor.read_bytes()).hexdigest(),
        "hayley": str(hayley.resolve()), "hayleySha256": hashlib.sha256(hayley.read_bytes()).hexdigest(),
        "output": str(output.resolve()), "outputSha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "sourceFrameRange": [SOURCE_START, SOURCE_END], "sourceFps": SOURCE_FPS,
        "targetFrameRange": [1, len(samples)], "targetFps": TARGET_FPS,
        "durationSeconds": (len(samples) - 1) / TARGET_FPS,
        "transferred": ["blink-left-right", "gaze", "smile", "jaw-open-limited-2deg"],
        "notTransferred": ["donor-face-geometry", "zero-valued-viseme-curves"],
        "hypothesis": "CuteGirl timing will add non-periodic facial life while Hayley's native facial bones preserve her identity.",
        "humanApproved": False, "releaseEligible": False,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    args = parse_args()
    report = build_hayley_cutegirl_face_performance_v503(args.donor, args.hayley, args.output, args.report)
    print(json.dumps({"iteration": report["iteration"], "durationSeconds": report["durationSeconds"], "transferred": report["transferred"]}))


if __name__ == "__main__":
    main()
