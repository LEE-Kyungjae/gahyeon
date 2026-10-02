#!/usr/bin/env python3
"""Prepare the curated Gahyeon SDXL LoRA v1 dataset without changing originals."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


SOURCE = Path("artifacts/gahyeon-ch")
OUTPUT = Path("artifacts/gahyeon-sdxl-v1")
VALIDATION = {3, 8, 15, 24, 29}
CAPTIONS = [
    "gahyeonch woman, happy close-up portrait, waving, white varsity jacket over a black graphic t-shirt, colorful wall background",
    "gahyeonch woman, full body, saluting, white varsity jacket over a black graphic t-shirt, denim shorts, outdoors, colorful wall",
    "gahyeonch woman, neutral close-up headshot, looking at viewer, white varsity jacket over a black graphic t-shirt",
    "gahyeonch woman, smiling close-up headshot, looking at viewer, white varsity jacket over a black graphic t-shirt",
    "gahyeonch woman, laughing close-up headshot, open smile, white varsity jacket over a black graphic t-shirt",
    "gahyeonch woman, three-quarter view close-up portrait, neutral expression, white varsity jacket over a black graphic t-shirt",
    "gahyeonch woman, left side profile portrait, white varsity jacket over a black graphic t-shirt",
    "gahyeonch woman, right side profile portrait, white varsity jacket over a black graphic t-shirt",
    "gahyeonch woman, high angle close-up portrait, neutral expression, white varsity jacket over a black graphic t-shirt",
    "gahyeonch woman, low angle close-up portrait, neutral expression, white varsity jacket over a black graphic t-shirt",
    "gahyeonch woman, smiling three-quarter view close-up portrait, white varsity jacket over a black graphic t-shirt",
    "gahyeonch woman, waist-up portrait, standing, neutral expression, white varsity jacket over a black graphic t-shirt",
    "gahyeonch woman, waist-up front view, standing, white varsity jacket over a black graphic t-shirt",
    "gahyeonch woman, three-quarter body portrait, arms crossed, white varsity jacket over a black graphic t-shirt",
    "gahyeonch woman, full body portrait, hand on hip, white varsity jacket over a black graphic t-shirt, denim shorts",
    "gahyeonch woman, full body front view, standing, white varsity jacket over a black graphic t-shirt, denim shorts",
    "gahyeonch woman, waist-up portrait, waving, white varsity jacket over a black graphic t-shirt",
    "gahyeonch woman, full body front view, standing, white varsity jacket over a black graphic t-shirt, denim shorts",
    "gahyeonch woman, full body side view, standing, white varsity jacket over a black graphic t-shirt, denim shorts",
    "gahyeonch woman, full body three-quarter side view, standing, white varsity jacket over a black graphic t-shirt, denim shorts",
    "gahyeonch woman, full body front view, relaxed standing pose, white varsity jacket over a black graphic t-shirt, denim shorts",
    "gahyeonch woman, full body three-quarter view, relaxed pose, white varsity jacket over a black graphic t-shirt, denim shorts",
    "gahyeonch woman, full body front view, standing outdoors, white varsity jacket over a black graphic t-shirt, denim shorts",
    "gahyeonch woman, upper body portrait indoors, white t-shirt, casual outfit, neutral expression",
    "gahyeonch woman, full body outdoors, black t-shirt and blue jeans, standing near concrete architecture",
    "gahyeonch woman, seated upper body portrait indoors, gray sweatshirt, relaxed expression",
    "gahyeonch woman, close-up portrait, ponytail, black t-shirt, looking at viewer",
    "gahyeonch woman, full body walking outdoors, white t-shirt and blue jeans, casual outfit",
    "gahyeonch woman, full body studio portrait, black dress, standing, neutral background",
]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> None:
    images = sorted(SOURCE.glob("*.png"))
    if len(images) != len(CAPTIONS):
        raise SystemExit(f"expected {len(CAPTIONS)} PNG files, found {len(images)}")

    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    train_dir = OUTPUT / "train" / "1_gahyeonch"
    validation_dir = OUTPUT / "validation"
    train_dir.mkdir(parents=True)
    validation_dir.mkdir(parents=True)

    manifest = {"trigger": "gahyeonch", "train": [], "validation": []}
    for index, (source, caption) in enumerate(zip(images, CAPTIONS), 1):
        split = "validation" if index in VALIDATION else "train"
        destination_dir = validation_dir if split == "validation" else train_dir
        stem = f"gahyeon_{index:02d}"
        image_destination = destination_dir / f"{stem}.png"
        shutil.copy2(source, image_destination)
        image_destination.with_suffix(".txt").write_text(caption + "\n", encoding="utf-8")
        manifest[split].append(
            {
                "index": index,
                "source": source.name,
                "file": str(image_destination.relative_to(OUTPUT)),
                "sha256": digest(source),
                "caption": caption,
            }
        )

    (OUTPUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"prepared {len(manifest['train'])} train and {len(manifest['validation'])} validation images")


if __name__ == "__main__":
    main()
