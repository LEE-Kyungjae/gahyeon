#!/usr/bin/env python3
"""Bake deterministic low-amplitude secondary motion onto existing auxiliary chains."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Quaternion


def parse_args():
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--character", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    return parser.parse_args(values)


def stable_phase(name: str) -> float:
    value = int(hashlib.sha256(name.encode("utf-8")).hexdigest()[:8], 16)
    return (value / 0xFFFFFFFF) * math.tau


def action_fcurves(action):
    curves = list(getattr(action, "fcurves", ()))
    for layer in getattr(action, "layers", ()):
        for strip in getattr(layer, "strips", ()):
            for bag in getattr(strip, "channelbags", ()):
                curves.extend(getattr(bag, "fcurves", ()))
    return curves


def bake_secondary_motion(source, profile_path, character_id, output, report_path):
    for path in (source, profile_path):
        if not path.is_file():
            raise FileNotFoundError(path)
    for path in (output, report_path):
        if path.exists():
            raise FileExistsError(f"refusing to overwrite immutable v613 output: {path}")
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    if character_id not in profile["characters"]:
        raise KeyError(f"character missing from profile: {character_id}")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(source.resolve()))
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    if len(armatures) != 1:
        raise RuntimeError(f"expected one armature, got {[obj.name for obj in armatures]}")
    armature = armatures[0]
    action = armature.animation_data.action if armature.animation_data else None
    if action is None:
        raise RuntimeError("input contains no active action")
    start = int(round(action.frame_range[0]))
    end = int(round(action.frame_range[1]))
    if end <= start:
        raise RuntimeError(f"invalid action range: {action.frame_range[:]}")
    scene = bpy.context.scene
    scene.frame_start = start
    scene.frame_end = end
    scene.render.fps = 30
    groups = profile["characters"][character_id]["groups"]
    configured = [
        (role, chain_index, chain, groups[role]["tuning"])
        for role in ("hair", "clothing")
        for chain_index, chain in enumerate(groups[role]["chains"])
    ]
    required = {name for _, _, chain, _ in configured for name in chain["bones"]}
    missing = sorted(required - set(armature.pose.bones.keys()))
    if missing:
        raise RuntimeError(f"secondary profile bones missing from FBX: {missing}")

    # Capture every source quaternion before inserting any new keys.
    base = {}
    for frame in range(start, end + 1):
        scene.frame_set(frame)
        base[frame] = {
            name: armature.pose.bones[name].rotation_quaternion.copy()
            for name in required
        }

    spans = end - start
    changed = set()
    peaks = {"hair": 0.0, "clothing": 0.0}
    for role, chain_index, chain, tuning in configured:
        bones = chain["bones"]
        max_angle = min(float(tuning["maxAngleDegrees"]), 4.0 if role == "hair" else 2.4)
        role_scale = 1.0 if role == "hair" else 0.72
        phase = stable_phase(f"{character_id}:{role}:{chain['root']}")
        for depth, name in enumerate(bones):
            bone = armature.pose.bones[name]
            bone.rotation_mode = "QUATERNION"
            depth_scale = (0.48 + 0.18 * depth) * role_scale
            for frame in range(start, end + 1):
                t = (frame - start) / spans
                # Integer-cycle harmonics make frame start/end exactly identical.
                lag = depth * 0.34
                sway = math.sin(math.tau * 2.0 * t + phase - lag)
                flutter = 0.32 * math.sin(math.tau * 3.0 * t + phase * 0.61 - lag * 1.4)
                x_degrees = max_angle * depth_scale * (0.58 * sway + 0.22 * flutter)
                z_degrees = max_angle * depth_scale * (0.31 * math.sin(math.tau * t + phase - lag))
                x_degrees = max(-max_angle, min(max_angle, x_degrees))
                z_degrees = max(-max_angle, min(max_angle, z_degrees))
                peaks[role] = max(peaks[role], abs(x_degrees), abs(z_degrees))
                delta = (
                    Quaternion((1.0, 0.0, 0.0), math.radians(x_degrees))
                    @ Quaternion((0.0, 0.0, 1.0), math.radians(z_degrees))
                )
                bone.rotation_quaternion = base[frame][name] @ delta
                bone.keyframe_insert("rotation_quaternion", frame=frame, group=name)
            changed.add(name)
    for curve in action_fcurves(action):
        for point in curve.keyframe_points:
            point.interpolation = "LINEAR"
    scene.frame_set(start)
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action="DESELECT")
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    output.parent.mkdir(parents=True, exist_ok=True)
    result = bpy.ops.export_scene.fbx(
        filepath=str(output.resolve()), use_selection=True, object_types={"ARMATURE"},
        apply_unit_scale=True, apply_scale_options="FBX_SCALE_ALL", add_leaf_bones=False,
        use_armature_deform_only=False, bake_anim=True, bake_anim_use_all_bones=True,
        bake_anim_use_nla_strips=False, bake_anim_use_all_actions=False,
        bake_anim_step=1.0, bake_anim_simplify_factor=0.0,
    )
    if "FINISHED" not in result or not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError(f"secondary-motion FBX export failed: {result}")
    report = {
        "schemaVersion": 1,
        "iteration": "v613",
        "status": "authored-draft-baked-secondary-motion",
        "character": character_id,
        "source": str(source.resolve()),
        "sourceSha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "profile": str(profile_path.resolve()),
        "profileSha256": hashlib.sha256(profile_path.read_bytes()).hexdigest(),
        "output": str(output.resolve()),
        "outputSha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "frameRange": [start, end],
        "fps": scene.render.fps,
        "changedBoneCount": len(changed),
        "changedBones": sorted(changed),
        "chainCounts": {role: groups[role]["chainCount"] for role in ("hair", "clothing")},
        "peakAddedRotationDegrees": peaks,
        "loopClosedByConstruction": True,
        "hypothesis": "Low-amplitude phase-lagged auxiliary rotations will add readable inertia without changing body, face, or retargeted locomotion.",
        "runtimePhysics": False,
        "humanApproved": False,
        "releaseEligible": False,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    args = parse_args()
    report = bake_secondary_motion(
        args.input, args.profile, args.character, args.output, args.report
    )
    print(json.dumps({
        "character": report["character"],
        "changedBoneCount": report["changedBoneCount"],
        "peakAddedRotationDegrees": report["peakAddedRotationDegrees"],
        "outputSha256": report["outputSha256"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
