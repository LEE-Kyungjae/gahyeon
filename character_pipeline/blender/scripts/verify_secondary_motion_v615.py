#!/usr/bin/env python3
"""Verify v613 with normalized action time across FBX exporter frame offsets."""

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


def load_animation(path: Path, fractions: tuple[float, ...]):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path.resolve()))
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    if len(armatures) != 1:
        raise RuntimeError(f"{path}: expected one armature, got {len(armatures)}")
    armature = armatures[0]
    action = armature.animation_data.action if armature.animation_data else None
    if action is None:
        raise RuntimeError(f"{path}: no action")
    start, end = (int(round(value)) for value in action.frame_range)
    frames = [int(round(start + fraction * (end - start))) for fraction in fractions]
    samples = {}
    for fraction, frame in zip(fractions, frames):
        bpy.context.scene.frame_set(frame)
        samples[fraction] = {
            bone.name: {
                "location": bone.location.copy(),
                "rotation": bone.rotation_quaternion.copy(),
                "scale": bone.scale.copy(),
            }
            for bone in armature.pose.bones
        }
    return {"bones": set(armature.pose.bones.keys()), "frameRange": [start, end], "frames": frames, "samples": samples}


def degrees_between(a, b):
    return math.degrees(a.rotation_difference(b).angle)


def verify(source, candidate, profile_path, character_id, output):
    for path in (source, candidate, profile_path):
        if not path.is_file():
            raise FileNotFoundError(path)
    if output.exists():
        raise FileExistsError(f"refusing to overwrite immutable v615 output: {output}")
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    groups = profile["characters"][character_id]["groups"]
    secondary = {
        name for role in ("hair", "clothing")
        for chain in groups[role]["chains"] for name in chain["bones"]
    }
    fractions = (0.0, 0.25, 0.5, 0.75, 1.0)
    base = load_animation(source, fractions)
    changed = load_animation(candidate, fractions)
    if base["bones"] != changed["bones"]:
        raise RuntimeError("source/candidate bone sets differ")
    body = base["bones"] - secondary
    max_body_rotation = max(
        degrees_between(base["samples"][f][name]["rotation"], changed["samples"][f][name]["rotation"])
        for f in fractions for name in body
    )
    max_body_location = max(
        (base["samples"][f][name]["location"] - changed["samples"][f][name]["location"]).length
        for f in fractions for name in body
    )
    max_body_scale = max(
        (base["samples"][f][name]["scale"] - changed["samples"][f][name]["scale"]).length
        for f in fractions for name in body
    )
    max_secondary_rotation = max(
        degrees_between(base["samples"][f][name]["rotation"], changed["samples"][f][name]["rotation"])
        for f in fractions for name in secondary
    )
    loop_delta = max(
        degrees_between(
            base["samples"][0.0][name]["rotation"].inverted() @ changed["samples"][0.0][name]["rotation"],
            base["samples"][1.0][name]["rotation"].inverted() @ changed["samples"][1.0][name]["rotation"],
        )
        for name in secondary
    )
    checks = {
        "durationPreserved": (base["frameRange"][1] - base["frameRange"][0]) == (changed["frameRange"][1] - changed["frameRange"][0]) == 305,
        "bodyRotationUnchanged": max_body_rotation <= 0.05,
        "bodyLocationUnchanged": max_body_location <= 0.001,
        "bodyScaleUnchanged": max_body_scale <= 0.001,
        "secondaryMotionPresent": max_secondary_rotation >= 0.25,
        "addedMotionLoopClosed": loop_delta <= 0.15,
    }
    report = {
        "schemaVersion": 1,
        "iteration": "v615",
        "status": "passed" if all(checks.values()) else "failed",
        "character": character_id,
        "source": str(source.resolve()),
        "candidate": str(candidate.resolve()),
        "timeMapping": {"fractions": fractions, "sourceFrames": base["frames"], "candidateFrames": changed["frames"]},
        "secondaryBoneCount": len(secondary),
        "bodyBoneCount": len(body),
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
