#!/usr/bin/env python3
"""Analyze and apply explicit non-destructive alpha correction layers."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def analyze_matte_edges(alpha: Image.Image) -> dict[str, Any]:
    alpha = alpha.convert("L"); width, height = alpha.size; pixels = alpha.load(); seen = set(); components = []
    for y in range(height):
        for x in range(width):
            if pixels[x, y] < 128 or (x, y) in seen:
                continue
            stack = [(x, y)]; seen.add((x, y)); count = 0; box = [x, y, x, y]
            while stack:
                px, py = stack.pop(); count += 1
                box = [min(box[0], px), min(box[1], py), max(box[2], px), max(box[3], py)]
                for point in ((px-1,py),(px+1,py),(px,py-1),(px,py+1)):
                    if 0 <= point[0] < width and 0 <= point[1] < height and point not in seen and pixels[point[0],point[1]] >= 128:
                        seen.add(point); stack.append(point)
            components.append({"pixels": count, "box": box})
    components.sort(key=lambda item: item["pixels"], reverse=True)
    histogram = alpha.histogram(); total = width * height
    return {"width": width, "height": height, "foregroundComponents": len(components),
            "smallComponentsBelow100Pixels": sum(item["pixels"] < 100 for item in components),
            "largestComponents": components[:12], "partialPixels": sum(histogram[1:255]),
            "transparentFraction": histogram[0]/total, "opaqueFraction": histogram[255]/total}


def apply_matte_corrections(config: dict[str, Any], source_rgba: Path, correction: dict[str, Any],
                            output: Path, manifest: Path) -> dict[str, Any]:
    if output.exists() or manifest.exists():
        raise ValueError("refusing to overwrite corrected matte")
    canonical = str(correction.get("canonicalIndex")); profiles = {r["id"]: r for r in config["roiProfiles"].get(canonical, [])}
    if not profiles:
        raise ValueError("unknown canonical correction profile")
    with Image.open(source_rgba) as source:
        source = source.convert("RGBA"); alpha = source.getchannel("A"); before = analyze_matte_edges(alpha)
        applied = []
        for item in correction.get("layers", []):
            if item.get("operation") not in config["operations"] or item.get("roi") not in profiles:
                raise ValueError("invalid correction operation or ROI")
            layer_path = Path(item.get("path", ""))
            if not layer_path.is_absolute() or not layer_path.is_file() or layer_path.is_symlink():
                raise ValueError("correction layer must be absolute regular file")
            if digest(layer_path) != item.get("sha256"):
                raise ValueError("correction layer checksum differs")
            with Image.open(layer_path) as layer_image:
                layer = layer_image.convert("L");
                if layer.size != source.size:
                    raise ValueError("correction layer dimensions differ")
                roi = profiles[item["roi"]]["box"]; layer_pixels = layer.load()
                bbox = layer.getbbox()
                if bbox and (bbox[0] < roi[0] or bbox[1] < roi[1] or bbox[2] > roi[2] or bbox[3] > roi[3]):
                    raise ValueError("correction layer escapes declared ROI")
                if item["operation"] == "add":
                    alpha = ImageChops.lighter(alpha, layer)
                elif item["operation"] == "remove":
                    alpha = ImageChops.subtract(alpha, layer)
                else:
                    alpha.paste(layer.crop(tuple(roi)), tuple(roi))
            applied.append({"operation": item["operation"], "roi": item["roi"], "sha256": item["sha256"]})
        result = source.copy(); result.putalpha(alpha); output.parent.mkdir(parents=True, exist_ok=True); result.save(output)
        after = analyze_matte_edges(alpha)
    record = {"schemaVersion": 1, "canonicalIndex": correction["canonicalIndex"],
              "source": {"path": str(source_rgba), "sha256": digest(source_rgba)},
              "output": {"path": str(output), "sha256": digest(output)}, "layers": applied,
              "before": before, "after": after, "status": "draft-awaiting-human-review",
              "approved": False, "reviewer": None, "reviewedAt": None,
              "rgbInvariant": "corrected RGB equals source RGBA RGB for every pixel"}
    manifest.write_text(json.dumps(record, indent=2)+"\n"); return record


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--config",type=Path,default=Path("character_pipeline/config/matte_correction.json")); parser.add_argument("--source",type=Path,required=True); parser.add_argument("--correction",type=Path,required=True); parser.add_argument("--output",type=Path,required=True); parser.add_argument("--manifest",type=Path,required=True)
    args=parser.parse_args(); print(json.dumps(apply_matte_corrections(json.loads(args.config.read_text()),args.source,json.loads(args.correction.read_text()),args.output,args.manifest))); return 0


if __name__=="__main__": raise SystemExit(main())
