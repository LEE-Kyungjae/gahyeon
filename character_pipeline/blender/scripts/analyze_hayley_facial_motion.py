#!/usr/bin/env python3
"""Measure safe facial-bone motion ranges from Hayley's original animation."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

import bpy


BONES = (
    "cJaw", "lEyelidUpperA", "lEyelidUpperB", "lEyelidLowerA", "lEyelidLowerB",
    "rEyelidUpperA", "rEyelidUpperB", "rEyelidLowerA", "rEyelidLowerB",
    "lLipCorner", "rLipCorner", "cLipUpper", "cLipLower",
    "lForeheadIn", "rForeheadIn", "cForehead", "lEye", "rEye",
)


def parse_args():
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(values)


def vector_record(values):
    return [round(value, 6) for value in values]


def analyze_hayley_facial_motion(source):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(source))
    armatures = [item for item in bpy.context.scene.objects if item.type == "ARMATURE"]
    if len(armatures) != 1:
        raise RuntimeError(f"expected one Hayley armature, found {len(armatures)}")
    armature = armatures[0]
    missing = [name for name in BONES if name not in armature.pose.bones]
    if missing:
        raise RuntimeError(f"missing Hayley facial bones: {missing}")
    action = armature.animation_data.action if armature.animation_data else None
    if action is None:
        raise RuntimeError("Hayley source has no active action")
    start, end = (round(value) for value in action.frame_range)
    samples = {name: [] for name in BONES}
    for frame in range(start, end + 1):
        bpy.context.scene.frame_set(frame)
        for name in BONES:
            matrix = armature.pose.bones[name].matrix_basis
            translation, rotation, scale = matrix.decompose()
            euler = rotation.to_euler("XYZ")
            samples[name].append({
                "frame": frame,
                "translation": tuple(translation),
                "rotationDegrees": tuple(math.degrees(value) for value in euler),
                "scale": tuple(scale),
            })
    ranges = {}
    animated = []
    for name, values in samples.items():
        translations = list(zip(*(item["translation"] for item in values)))
        rotations = list(zip(*(item["rotationDegrees"] for item in values)))
        translation_range = [max(axis) - min(axis) for axis in translations]
        rotation_range = [max(axis) - min(axis) for axis in rotations]
        is_animated = max((*translation_range, *rotation_range)) > 1e-5
        if is_animated:
            animated.append(name)
        ranges[name] = {
            "animated": is_animated,
            "translationMin": vector_record(min(axis) for axis in translations),
            "translationMax": vector_record(max(axis) for axis in translations),
            "rotationDegreesMin": vector_record(min(axis) for axis in rotations),
            "rotationDegreesMax": vector_record(max(axis) for axis in rotations),
        }
    return {
        "schemaVersion": 1,
        "iteration": "v387",
        "status": "measured-native-facial-bone-motion-ranges",
        "source": str(source.resolve()),
        "armature": armature.name,
        "action": action.name,
        "frameRange": [start, end],
        "sampleCount": end - start + 1,
        "animatedBones": animated,
        "bones": ranges,
        "policy": {
            "useAsInitialCalibrationBoundsOnly": True,
            "visualValidationRequired": True,
            "automaticApproval": False,
        },
    }


def main():
    args = parse_args()
    if not args.input.is_file():
        raise FileNotFoundError(args.input)
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite analysis: {args.output}")
    report = analyze_hayley_facial_motion(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({
        "action": report["action"],
        "frameRange": report["frameRange"],
        "animatedBones": report["animatedBones"],
    }))


if __name__ == "__main__":
    main()
