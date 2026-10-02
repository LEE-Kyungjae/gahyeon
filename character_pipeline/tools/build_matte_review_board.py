#!/usr/bin/env python3
"""Build source/checker/alpha contact sheet for human matte review."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


def build_board(source: Path, rgba: Path, output: Path) -> None:
    if output.exists():
        raise ValueError("refusing to overwrite review board")
    with Image.open(source) as src, Image.open(rgba) as cutout:
        src = src.convert("RGB"); cutout = cutout.convert("RGBA")
        if src.size != cutout.size:
            raise ValueError("review inputs differ in size")
        width = 480; height = round(src.height * width / src.width)
        src = src.resize((width, height), Image.Resampling.LANCZOS)
        cutout = cutout.resize((width, height), Image.Resampling.LANCZOS)
        checker = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(checker); tile = 24
        for y in range(0, height, tile):
            for x in range(0, width, tile):
                if (x // tile + y // tile) % 2:
                    draw.rectangle((x, y, x + tile - 1, y + tile - 1), fill=(150, 150, 150))
        checker.paste(cutout, mask=cutout.getchannel("A"))
        alpha = ImageOps.grayscale(cutout.getchannel("A")).convert("RGB")
        label = 42; board = Image.new("RGB", (width * 3, height + label), (25, 25, 25))
        for index, (title, image) in enumerate((("CANONICAL RGB", src), ("CHECKERBOARD", checker), ("ALPHA", alpha))):
            board.paste(image, (index * width, label))
            ImageDraw.Draw(board).text((index * width + 12, 12), title, fill="white")
        output.parent.mkdir(parents=True, exist_ok=True)
        board.save(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--rgba", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(); build_board(args.source, args.rgba, args.output); return 0


if __name__ == "__main__": raise SystemExit(main())
