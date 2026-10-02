#!/usr/bin/env python3
"""Deterministically compare same-camera PNG renders without inventing quality."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


def compare(first: Path, second: Path) -> dict:
    a = np.asarray(Image.open(first).convert("RGBA"), dtype=np.int16)
    b = np.asarray(Image.open(second).convert("RGBA"), dtype=np.int16)
    if a.shape != b.shape:
        raise ValueError(f"image dimensions differ: {a.shape} vs {b.shape}")
    delta = np.abs(a - b)
    return {
        "first": str(first), "second": str(second),
        "dimensions": [a.shape[1], a.shape[0]],
        "meanAbsoluteError255": round(float(delta.mean()), 6),
        "maxAbsoluteError255": int(delta.max()),
        "pixelsAbove2": int(np.any(delta[:, :, :3] > 2, axis=2).sum()),
        "pixelCount": int(a.shape[0] * a.shape[1]),
        "identical": bool(np.array_equal(a, b)),
        "qualityClaim": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("first", type=Path)
    parser.add_argument("second", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    value = compare(args.first, args.second)
    payload = json.dumps(value, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

