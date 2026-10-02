#!/usr/bin/env python3
"""Verify baked secondary motion changes only configured chains and closes its loop."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

import bpy


def parse_args():
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--character", required=True)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(values)


def load_samples(path: Path, frames: list[int]):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path.resolve()))
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    if len(armatures) != 1:
        raise RuntimeError(f"{path}: expected one armature, got {len(armatures)}")
    armature = armatures[0]
    action = armature.animation_data.action if armature.animation_data else None
    if action is None:
        raise RuntimeError(f"{path}: no action")
    samples = {}
    for frame in frames:
        bpy.context.scene.frame_set(frame)
        samples[frame] = {
            bone.name: {
                "location": bone.location.copy(),
                "rotation": bone.rotation_quaternion.copy(),
                "scale": bone.scale.copy(),
            }
            for bone in armature.pose.bones
        }
    return {
        "bones": set(armature.pose.bones.keys()),
        "frameRange": [int(round(action.frame_range[0])), int(round(action.frame_range[1]))],
        "samples": samples,
    }


def degrees_between(a, b):
    return math.degrees(a.rotation_difference(b).angle)


def verify_secondary_motion(source, candidate, profile_path, character_id, output):
    for path in (source, candidate, profile_path):
        if not path.is_file():
            raise FileNotFoundError(path)
    if output.exists():
        raise FileExistsError(f"refusing to overwrite immutable v614 output: {output}")
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    groups = profile["characters"][character_id]["groups"]
    secondary = {
        name
        for role in ("hair", "clothing")
        for chain in groups[role]["chains"]
        for name in chain["bones"]
    }
    frames = [1, 77, 153, 229, 306]
    base = load_samples(source, frames)
    changed = load_samples(candidate, frames)
    if base["bones"] != changed["bones"]:
        raise RuntimeError("source/candidate bone sets differ")
    body = base["bones"] - secondary
    max_body_rotation = 0.0
    max_body_location = 0.0
    max_body_scale = 0.0
    max_secondary_rotation = 0.0
    for frame in frames:
        for name in body:
            before, after = base["samples"][frame][name], changed["samples"][frame][name]
            max_body_rotation = max(max_body_rotation, degrees_between(before["rotation"], after["rotation"]))
            max_body_location = max(max_body_location, (before["location"] - after["location"]).length)
            max_body_scale = max(max_body_scale, (before["scale"] - after["scale"]).length)
        for name in secondary:
            max_secondary_rotation = max(
                max_secondary_rotation,
                degrees_between(base["samples"][frame][name]["rotation"], changed["samples"][frame][name]["rotation"]),
            )
    loop_delta = 0.0
    for name in secondary:
        start_added = base["samples"][1][name]["rotation"].inverted() @ changed["samples"][1][name]["rotation"]
        end_added = base["samples"][306][name]["rotation"].inverted() @ changed["samples"][306][name]["rotation"]
        loop_delta = max(loop_delta, degrees_between(start_added, end_added))
    checks = {
        "frameRangePreserved": base["frameRange"] == changed["frameRange"] == [1, 306],
        "bodyRotationUnchanged": max_body_rotation <= 0.05,
        "bodyLocationUnchanged": max_body_location <= 0.001,
        "bodyScaleUnchanged": max_body_scale <= 0.001,
        "secondaryMotionPresent": max_secondary_rotation >= 0.25,
        "addedMotionLoopClosed": loop_delta <= 0.05,
    }
    report = {
        "schemaVersion": 1,
        "iteration": "v614",
        "status": "passed" if all(checks.values()) else "failed",
        "character": character_id,
        "source": str(source.resolve()),
        "candidate": str(candidate.resolve()),
        "secondaryBoneCount": len(secondary),
        "bodyBoneCount": len(body),
        "sampleFrames": frames,
        "metrics": {
            "maxBodyRotationDeltaDegrees": max_body_rotation,
            "maxBodyLocationDelta": max_body_location,
            "maxBodyScaleDelta": max_body_scale,
            "maxSecondaryRotationDeltaDegrees": max_secondary_rotation,
            "addedMotionLoopClosureDeltaDegrees": loop_delta,
        },
        "checks": checks,
        "humanApproved": False,
        "releaseEligible": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if not all(checks.values()):
        raise RuntimeError(json.dumps(report, sort_keys=True))
    return report


def main():
    args = parse_args()
    report = verify_secondary_motion(
        args.source, args.candidate, args.profile, args.character, args.output
    )
    print(json.dumps({"character": report["character"], "status": report["status"], "metrics": report["metrics"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
