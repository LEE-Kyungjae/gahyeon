#!/usr/bin/env python3
"""Compare normalized world-space bone endpoints across FBX representations."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def parse_args():
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--character", required=True)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(values)


def load_world(path: Path, fractions):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path.resolve()))
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    if len(armatures) != 1:
        raise RuntimeError(f"{path}: expected one armature")
    armature = armatures[0]
    action = armature.animation_data.action if armature.animation_data else None
    start, end = (int(round(value)) for value in action.frame_range)
    frames = [int(round(start + fraction * (end - start))) for fraction in fractions]
    samples = {}
    for fraction, frame in zip(fractions, frames):
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        points = {}
        for bone in armature.pose.bones:
            matrix = armature.matrix_world @ bone.matrix
            head = matrix.translation.copy()
            axis = (matrix.to_3x3() @ Vector((0.0, bone.length, 0.0)))
            points[bone.name] = {"head": head, "tail": head + axis}
        root_name = next(b.name for b in armature.pose.bones if b.parent is None)
        root = points[root_name]["head"]
        scale = max((value["head"] - root).length for value in points.values())
        samples[fraction] = {
            name: {
                "head": (value["head"] - root) / scale,
                "direction": (value["tail"] - value["head"]).normalized(),
            }
            for name, value in points.items()
        }
    return {"bones": set(armature.pose.bones.keys()), "frameRange": [start, end], "frames": frames, "samples": samples}


def angle_degrees(a, b):
    dot = max(-1.0, min(1.0, a.dot(b)))
    return math.degrees(math.acos(dot))


def verify(source, candidate, profile_path, character_id, output):
    for path in (source, candidate, profile_path):
        if not path.is_file():
            raise FileNotFoundError(path)
    if output.exists():
        raise FileExistsError(f"refusing to overwrite immutable v616 output: {output}")
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    groups = profile["characters"][character_id]["groups"]
    secondary = {
        name for role in ("hair", "clothing")
        for chain in groups[role]["chains"] for name in chain["bones"]
    }
    fractions = (0.0, 0.25, 0.5, 0.75, 1.0)
    base = load_world(source, fractions)
    changed = load_world(candidate, fractions)
    if base["bones"] != changed["bones"]:
        raise RuntimeError("source/candidate bone sets differ")
    body = base["bones"] - secondary
    max_body_position = max(
        (base["samples"][f][name]["head"] - changed["samples"][f][name]["head"]).length
        for f in fractions for name in body
    )
    max_body_direction = max(
        angle_degrees(base["samples"][f][name]["direction"], changed["samples"][f][name]["direction"])
        for f in fractions for name in body
    )
    max_secondary_direction = max(
        angle_degrees(base["samples"][f][name]["direction"], changed["samples"][f][name]["direction"])
        for f in fractions for name in secondary
    )
    checks = {
        "durationPreserved": (base["frameRange"][1] - base["frameRange"][0]) == (changed["frameRange"][1] - changed["frameRange"][0]) == 305,
        "bodyJointPositionsPreserved": max_body_position <= 0.002,
        "bodyBoneDirectionsPreserved": max_body_direction <= 0.15,
        "secondaryDirectionMotionPresent": max_secondary_direction >= 0.25,
    }
    report = {
        "schemaVersion": 1,
        "iteration": "v616",
        "status": "passed" if all(checks.values()) else "failed",
        "character": character_id,
        "source": str(source.resolve()),
        "candidate": str(candidate.resolve()),
        "timeMapping": {"fractions": fractions, "sourceFrames": base["frames"], "candidateFrames": changed["frames"]},
        "metrics": {
            "maxNormalizedBodyJointPositionDelta": max_body_position,
            "maxBodyBoneDirectionDeltaDegrees": max_body_direction,
            "maxSecondaryBoneDirectionDeltaDegrees": max_secondary_direction,
        },
        "checks": checks,
        "humanApproved": False,
        "releaseEligible": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if report["status"] != "passed":
        raise RuntimeError(json.dumps(report, sort_keys=True))
    return report


def main():
    args = parse_args()
    report = verify(args.source, args.candidate, args.profile, args.character, args.output)
    print(json.dumps({"character": report["character"], "status": report["status"], "metrics": report["metrics"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
