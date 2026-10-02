#!/usr/bin/env python3
"""Render deterministic canonical and supporting modeling reference boards."""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
PACK_DIR = ROOT / "artifacts/gahyeon-ch"
MANIFEST = PACK_DIR / "identity-reference.json"
OUTPUT = PACK_DIR / "identity-reference-board.png"
SUPPORTING_OUTPUT = PACK_DIR / "identity-supporting-board.png"
CELL = (270, 330)
LABEL_HEIGHT = 42
MARGIN = 18
COLS = 6


def selected_font(size: int):
    for path in (
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ):
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def render(refs: list[dict], output: Path, supporting: bool = False) -> None:
    refs = sorted(refs, key=lambda item: (item["kind"] != "face", item["index"]))
    rows = (len(refs) + COLS - 1) // COLS
    width = MARGIN * 2 + COLS * CELL[0]
    height = MARGIN * 2 + rows * (CELL[1] + LABEL_HEIGHT)
    board = Image.new("RGB", (width, height), "#15171a")
    draw = ImageDraw.Draw(board)
    label_font = selected_font(17)

    for offset, reference in enumerate(refs):
        row, column = divmod(offset, COLS)
        x = MARGIN + column * CELL[0]
        y = MARGIN + row * (CELL[1] + LABEL_HEIGHT)
        with Image.open(PACK_DIR / reference["file"]) as source:
            fitted = ImageOps.fit(source.convert("RGB"), CELL, method=Image.Resampling.LANCZOS, centering=(0.5, 0.35))
        board.paste(fitted, (x, y))
        prefix = "SUP " if supporting else ""
        label = f'{reference["index"]:02d}  {prefix}{reference["kind"]} / {reference["view"]}'
        draw.text((x + 6, y + CELL[1] + 9), label, font=label_font, fill="#f4f4f4")
        draw.rectangle((x, y, x + CELL[0] - 1, y + CELL[1] - 1), outline="#666b73", width=1)

    board.save(output, optimize=True)
    print(output.relative_to(ROOT))


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    render(manifest["references"], OUTPUT)
    render(manifest["supportingReferences"], SUPPORTING_OUTPUT, supporting=True)


if __name__ == "__main__":
    main()
