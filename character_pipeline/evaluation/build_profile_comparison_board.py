#!/usr/bin/env python3
"""Build a labeled, non-destructive profile comparison board."""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


def tile(path: Path, label: str, size: tuple[int, int]) -> Image.Image:
    image = Image.open(path).convert("RGB")
    image = ImageOps.contain(image, (size[0], size[1] - 54))
    canvas = Image.new("RGB", size, (48, 50, 55))
    canvas.paste(image, ((size[0] - image.width) // 2, 46 + (size[1] - 54 - image.height) // 2))
    ImageDraw.Draw(canvas).text((14, 14), label, fill=(245, 245, 245), font=ImageFont.load_default())
    return canvas


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--canonical-left", type=Path, required=True)
    parser.add_argument("--candidate-left", type=Path, required=True)
    parser.add_argument("--canonical-right", type=Path, required=True)
    parser.add_argument("--candidate-right", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite: {args.output}")
    size = (700, 900)
    images = [
        tile(args.canonical_left, "Canonical 07 - left profile authority", size),
        tile(args.candidate_left, "v79 Go v3 - left profile candidate", size),
        tile(args.canonical_right, "Canonical 08 - right profile authority", size),
        tile(args.candidate_right, "v79 Go v3 - right profile candidate", size),
    ]
    board = Image.new("RGB", (size[0] * 2, size[1] * 2), (36, 38, 42))
    for index, image in enumerate(images):
        board.paste(image, ((index % 2) * size[0], (index // 2) * size[1]))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    board.save(args.output, quality=95)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
