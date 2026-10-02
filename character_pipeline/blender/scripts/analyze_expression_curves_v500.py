#!/usr/bin/env python3
"""Measure semantic expression timing from a shape-key animation donor."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

import bpy


SEMANTIC_PATTERNS = {
    "blinkLeft": (r"eye[_ ]?blink[_ ]?l(?:eft)?$",),
    "blinkRight": (r"eye[_ ]?blink[_ ]?r(?:ight)?$",),
    "smileLeft": (r"mouth[_ ]?smile[_ ]?l(?:eft)?$",),
    "smileRight": (r"mouth[_ ]?smile[_ ]?r(?:ight)?$",),
    "jawOpen": (r"jaw[_ ]?(?:open|down)$", r"^v[_ ]?open$"),
    "mouthClose": (r"mouth[_ ]?close$",),
    "visemeOpen": (r"^v[_ ]?open$", r"^v[_ ]?lip[_ ]?open$"),
    "visemeExplosive": (r"^v[_ ]?explosive$",),
    "visemeDentalLip": (r"^v[_ ]?dental[_ ]?lip$",),
    "visemeTightO": (r"^v[_ ]?tight[_ ]?o$",),
    "visemeWide": (r"^v[_ ]?wide$",),
    "visemeAffricate": (r"^v[_ ]?affricate$",),
    "eyeLookLeft": (r"eye_[lr]_look_l$",),
    "eyeLookRight": (r"eye_[lr]_look_r$",),
    "eyeLookUp": (r"eye_[lr]_look_up$",),
    "eyeLookDown": (r"eye_[lr]_look_down$",),
}


def parse_args():
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--iteration", default="v500")
    return parser.parse_args(values)


def action_fcurves(action):
    if hasattr(action, "fcurves"):
        return list(action.fcurves)
    curves = []
    for layer in action.layers:
        for strip in layer.strips:
            for channelbag in strip.channelbags:
                curves.extend(channelbag.fcurves)
    return curves


def shape_name(data_path):
    match = re.search(r'key_blocks\["(.+?)"\]\.value$', data_path)
    return match.group(1) if match else None


def semantic_for(name):
    normalized = name.lower().replace("-", "_")
    return [
        semantic for semantic, patterns in SEMANTIC_PATTERNS.items()
        if any(re.search(pattern, normalized) for pattern in patterns)
    ]


def analyze_expression_curves(source: Path, iteration: str):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(source))
    records = []
    for action in bpy.data.actions:
        for curve in action_fcurves(action):
            name = shape_name(curve.data_path)
            if not name:
                continue
            semantics = semantic_for(name)
            if not semantics:
                continue
            start, end = (int(round(value)) for value in action.frame_range)
            values = [(frame, float(curve.evaluate(frame))) for frame in range(start, end + 1)]
            peak_frame, peak_value = max(values, key=lambda pair: abs(pair[1]))
            active = [(frame, value) for frame, value in values if abs(value) >= max(0.05, abs(peak_value) * 0.25)]
            records.append({
                "action": action.name,
                "channel": name,
                "semantics": semantics,
                "frameRange": [start, end],
                "peakFrame": peak_frame,
                "peakValue": peak_value,
                "activeFrameRange": [active[0][0], active[-1][0]] if active else None,
                "keyframes": [[int(point.co.x), float(point.co.y)] for point in curve.keyframe_points],
            })
    return {
        "schemaVersion": 1,
        "iteration": iteration,
        "status": "measured-expression-timing-draft",
        "source": str(source.resolve()),
        "sourceSha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "fps": bpy.context.scene.render.fps,
        "semanticCurveCount": len(records),
        "curves": records,
        "policy": {
            "timingOnly": True,
            "copyDonorGeometry": False,
            "visualValidationRequired": True,
            "humanApproved": False,
        },
    }


def main():
    args = parse_args()
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite: {args.output}")
    report = analyze_expression_curves(args.input, args.iteration)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"curves": report["semanticCurveCount"], "fps": report["fps"]}))


if __name__ == "__main__":
    main()
