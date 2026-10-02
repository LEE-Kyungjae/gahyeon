#!/usr/bin/env python3
"""Extract a transparent MetaHuman frame sequence with one reusable rembg session."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image
from rembg import new_session, remove


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def process_frames(input_dir: Path, output_dir: Path, expected_count: int, model: str) -> dict:
    frames = sorted(input_dir.glob("*.png"))
    if len(frames) != expected_count:
        raise RuntimeError(f"expected {expected_count} PNG frames, found {len(frames)}")
    if output_dir.exists():
        raise RuntimeError(f"refusing to overwrite existing output: {output_dir}")

    output_dir.mkdir(parents=True)
    session = new_session(model)
    outputs = []
    for index, source in enumerate(frames, start=1):
        destination = output_dir / f"{index:04d}.png"
        with Image.open(source) as image:
            result = remove(image.convert("RGB"), session=session, alpha_matting=False)
            result.save(destination, format="PNG", optimize=True)
        outputs.append(destination)
        if index == 1 or index % 25 == 0 or index == len(frames):
            print(f"processed {index}/{len(frames)}", flush=True)

    return {
        "status": "completed",
        "hardwareVerified": False,
        "characterBlueprint": "/Game/Gahyeon/CharacterPipeline/v088/AssembledMedium/Skotukeda_WardrobeGroomQA_v088/BP_Skotukeda_WardrobeGroomQA_v088",
        "model": model,
        "frameCount": len(outputs),
        "firstFrame": {"path": str(outputs[0]), "sha256": sha256(outputs[0])},
        "lastFrame": {"path": str(outputs[-1]), "sha256": sha256(outputs[-1])},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--expected-count", type=int, default=211)
    parser.add_argument("--model", default="u2net_human_seg")
    args = parser.parse_args()

    result = process_frames(args.input_dir, args.output_dir, args.expected_count, args.model)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
