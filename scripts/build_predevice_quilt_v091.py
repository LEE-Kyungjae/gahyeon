#!/usr/bin/env python3
"""Build a monitor-review quilt that can never attest physical LG success."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "config/desktop-looking-glass-runtime-poc-v091.json"


def build_quilt(source: Path, output: Path, config_path: Path) -> dict:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    lg = config["lookingGlass"]
    if lg["verificationState"] != "hardware-unverified":
        raise ValueError("pre-device quilt must remain hardware-unverified")
    width, height = lg["quiltWidth"], lg["quiltHeight"]
    columns, rows, views = lg["columns"], lg["rows"], lg["views"]
    if columns * rows != views or width % columns or height % rows:
        raise ValueError("quilt grid does not divide evenly")
    tile_w, tile_h = width // columns, height // rows
    image = Image.open(source).convert("RGB")
    quilt = Image.new("RGB", (width, height), "black")
    for view in range(views):
        # Diagnostic-only pseudo views make ordering visible; they are not parallax renders.
        scale = max(tile_w / image.width, tile_h / image.height)
        resized = image.resize((round(image.width * scale), round(image.height * scale)))
        span = max(0, resized.width - tile_w)
        x = round(span * view / max(1, views - 1))
        tile = resized.crop((x, 0, x + tile_w, tile_h))
        draw = ImageDraw.Draw(tile)
        draw.rectangle((0, 0, 92, 24), fill="black")
        draw.text((6, 5), f"SIM {view + 1:02d}/{views}", fill="white")
        quilt.paste(tile, ((view % columns) * tile_w, (view // columns) * tile_h))
    output.parent.mkdir(parents=True, exist_ok=True)
    quilt.save(output)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    report = {
        "schemaVersion": 1,
        "status": "hardware-unverified",
        "physicalDeviceActive": False,
        "calibrationObserved": False,
        "realParallaxCapture": False,
        "source": str(source), "output": str(output), "sha256": digest,
        "width": width, "height": height, "views": views,
        "columns": columns, "rows": rows, "tileWidth": tile_w, "tileHeight": tile_h,
        "viewOrder": lg["viewOrder"],
    }
    output.with_suffix(".json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(json.dumps(build_quilt(args.source.resolve(), args.output.resolve(), args.config.resolve()), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
