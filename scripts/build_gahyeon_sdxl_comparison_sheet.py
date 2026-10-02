#!/usr/bin/env python3
"""Build the fixed-layout contact sheet for the Gahyeon LoRA checkpoint comparison."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path("artifacts/gahyeon-sdxl-v1-comparison")
IMAGES = ROOT / "images"
OUTPUT = ROOT / "comparison-sheet.png"
ROWS = ["front_portrait", "profile_smile", "casual_fullbody", "black_dress"]
COLUMNS = ["base", "step0200", "step0400", "step0600", "step0800"]
LABELS = ["BASE", "STEP 200", "STEP 400", "STEP 600", "STEP 800"]
CELL_WIDTH = 320
CELL_HEIGHT = 400
HEADER_HEIGHT = 52
ROW_LABEL_WIDTH = 150


def font(size: int):
    candidates = [
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def centered(draw, box, label, selected_font, fill):
    bounds = draw.textbbox((0, 0), label, font=selected_font)
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    x0, y0, x1, y1 = box
    draw.text(((x0 + x1 - width) / 2, (y0 + y1 - height) / 2), label, font=selected_font, fill=fill)


def main():
    build_sheet(COLUMNS, LABELS, OUTPUT)
    high_step_columns = ["step0800", "total1200", "total1600", "total2000", "total2400", "total2800"]
    high_step_labels = ["STEP 800", "STEP 1200", "STEP 1600", "STEP 2000", "STEP 2400", "STEP 2800"]
    if all(list(IMAGES.glob(f"{scenario}_{variant}_*.png")) for scenario in ROWS for variant in high_step_columns):
        build_sheet(high_step_columns, high_step_labels, ROOT / "comparison-sheet-highsteps.png")


def build_sheet(columns, labels, output):
    width = ROW_LABEL_WIDTH + CELL_WIDTH * len(columns)
    height = HEADER_HEIGHT + CELL_HEIGHT * len(ROWS)
    sheet = Image.new("RGB", (width, height), "#15171a")
    draw = ImageDraw.Draw(sheet)
    header_font = font(22)
    row_font = font(18)

    for column, label in enumerate(labels):
        x0 = ROW_LABEL_WIDTH + column * CELL_WIDTH
        centered(draw, (x0, 0, x0 + CELL_WIDTH, HEADER_HEIGHT), label, header_font, "#f4f4f4")

    for row, scenario in enumerate(ROWS):
        y0 = HEADER_HEIGHT + row * CELL_HEIGHT
        centered(draw, (0, y0, ROW_LABEL_WIDTH, y0 + CELL_HEIGHT), scenario.replace("_", "\n"), row_font, "#f4f4f4")
        for column, variant in enumerate(columns):
            matches = sorted(IMAGES.glob(f"{scenario}_{variant}_*.png"))
            if len(matches) != 1:
                raise RuntimeError(f"expected one image for {scenario}/{variant}, found {len(matches)}")
            with Image.open(matches[0]) as source:
                image = ImageOps.contain(source.convert("RGB"), (CELL_WIDTH - 8, CELL_HEIGHT - 8))
            x = ROW_LABEL_WIDTH + column * CELL_WIDTH + (CELL_WIDTH - image.width) // 2
            y = y0 + (CELL_HEIGHT - image.height) // 2
            sheet.paste(image, (x, y))
            draw.rectangle(
                (ROW_LABEL_WIDTH + column * CELL_WIDTH, y0, ROW_LABEL_WIDTH + (column + 1) * CELL_WIDTH - 1, y0 + CELL_HEIGHT - 1),
                outline="#4b5058",
                width=1,
            )

    sheet.save(output, optimize=True)
    print(output)


if __name__ == "__main__":
    main()
