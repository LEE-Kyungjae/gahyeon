#!/usr/bin/env python3
"""Measure fixed-view render legibility without claiming artistic quality."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


def evaluate(path: Path, expected: tuple[int, int], *, face_view: bool) -> dict:
    rgb = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32)
    height, width, _ = rgb.shape
    sample = max(4, min(width, height) // 100)
    corners = np.concatenate((
        rgb[:sample, :sample].reshape(-1, 3), rgb[:sample, -sample:].reshape(-1, 3),
        rgb[-sample:, :sample].reshape(-1, 3), rgb[-sample:, -sample:].reshape(-1, 3),
    ))
    background = np.median(corners, axis=0)
    distance = np.linalg.norm(rgb - background, axis=2)
    foreground = distance > 12.0
    ys, xs = np.where(foreground)
    defects = []
    if (width, height) != expected:
        defects.append("resolution-mismatch")
    if not len(xs):
        defects.append("no-visible-subject")
        bounds = None
        occupancy = 0.0
        luma = np.array([], dtype=np.float32)
        margins = None
    else:
        left, right, top, bottom = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
        bounds = [left, top, right, bottom]
        bbox_width, bbox_height = right - left + 1, bottom - top + 1
        occupancy = float(foreground.mean())
        margins = {
            "left": round(left / width, 6), "right": round((width - 1 - right) / width, 6),
            "top": round(top / height, 6), "bottom": round((height - 1 - bottom) / height, 6),
        }
        luma_all = 0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]
        luma = luma_all[foreground]
        if min(margins.values()) < 0.008:
            defects.append("subject-clipped-or-too-close-to-frame")
        height_fraction = bbox_height / height
        width_fraction = bbox_width / width
        if face_view and not (0.55 <= height_fraction <= 0.94):
            defects.append("face-framing-out-of-range")
        if not face_view and not (0.70 <= height_fraction <= 0.97):
            defects.append("body-framing-out-of-range")
        if width_fraction < (0.35 if face_view else 0.25):
            defects.append("subject-too-small-horizontally")
        if np.percentile(luma, 50) < 55.0 or np.percentile(luma, 90) < 85.0:
            defects.append("foreground-too-dark")
        if np.mean(luma < 18.0) > 0.20:
            defects.append("excessive-crushed-shadow")
        if np.mean(luma > 245.0) > 0.03:
            defects.append("excessive-highlight-clipping")
    return {
        "uri": str(path), "dimensions": [width, height],
        "expectedDimensions": list(expected), "viewClass": "face" if face_view else "body",
        "backgroundMedianRgb": [round(float(value), 3) for value in background],
        "foreground": {
            "thresholdRgbDistance": 12.0, "pixelFraction": round(occupancy, 6),
            "boundsPixels": bounds, "marginsFraction": margins,
            "luminance255": None if not len(luma) else {
                "p10": round(float(np.percentile(luma, 10)), 3),
                "p50": round(float(np.percentile(luma, 50)), 3),
                "p90": round(float(np.percentile(luma, 90)), 3),
            },
        },
        "validCapture": not defects, "defects": defects,
        "qualityClaim": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("--width", type=int, default=1440)
    parser.add_argument("--height", type=int, default=2560)
    parser.add_argument("--view-class", choices=("face", "body"), required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate(args.image.resolve(), (args.width, args.height), face_view=args.view_class == "face")
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        if args.output.exists():
            raise SystemExit(f"refusing to overwrite: {args.output}")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["validCapture"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
