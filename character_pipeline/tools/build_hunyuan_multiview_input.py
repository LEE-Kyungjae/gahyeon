#!/usr/bin/env python3
"""Build an immutable, provenance-checked Hunyuan multiview shape input package."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageOps


VIEW_MAP = {
    "front": 3,
    "left": 7,
    "right": 8,
}


def digest_hunyuan_input(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def verify_canonical_source(reference: dict, source: Path) -> None:
    if reference.get("identityAuthority") != "canonical":
        raise ValueError(f"reference is not canonical identity authority: {source.name}")
    if not source.is_file():
        raise FileNotFoundError(source)
    actual = digest_hunyuan_input(source)
    if actual != reference.get("sha256"):
        raise ValueError(f"canonical source checksum differs: {source.name}")


def normalize_hunyuan_reference(source: Path, destination: Path, size: int) -> dict:
    with Image.open(source) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
        original_size = list(image.size)
        image.thumbnail((size, size), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (size, size), (127, 127, 127))
        offset = ((size - image.width) // 2, (size - image.height) // 2)
        canvas.paste(image, offset)
        canvas.save(destination, format="PNG", optimize=True)
    return {
        "sourceDimensions": original_size,
        "outputDimensions": [size, size],
        "normalization": "contain-with-neutral-gray-padding-no-crop-no-geometry-warp",
        "sha256": digest_hunyuan_input(destination),
    }


def build_hunyuan_multiview_package(identity: Path, source_root: Path,
                                     output: Path, size: int = 1024) -> dict:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite immutable output: {output}")
    catalog = json.loads(identity.read_text(encoding="utf-8"))
    references = {item["index"]: item for item in catalog.get("references", [])}
    missing = sorted(set(VIEW_MAP.values()) - set(references))
    if missing:
        raise ValueError(f"identity manifest lacks required references: {missing}")

    output.mkdir(parents=True)
    views = {}
    try:
        for role, index in VIEW_MAP.items():
            reference = references[index]
            source = source_root / reference["file"]
            verify_canonical_source(reference, source)
            destination = output / f"{role}.png"
            normalized = normalize_hunyuan_reference(source, destination, size)
            views[role] = {
                "canonicalIndex": index,
                "canonicalView": reference["view"],
                "source": str(source),
                "sourceSha256": reference["sha256"],
                "file": destination.name,
                **normalized,
            }

        manifest = {
            "schemaVersion": 1,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "characterId": catalog.get("characterId"),
            "purpose": "temporary-multiview-geometry-estimation",
            "targetModel": "Tencent-Hunyuan/Hunyuan3D-2mv",
            "views": views,
            "missingViews": ["back"],
            "backViewPolicy": "absent-no-authoritative-source-do-not-fabricate",
            "identityAuthority": "user-provided-canonical-originals",
            "limitations": [
                "profile images are used as left/right shape constraints",
                "hair and clothing may contaminate reconstruction geometry",
                "output is not production topology and must not bypass MetaHuman conform",
                "model license must be approved before production use",
            ],
            "productionMeshAllowed": False,
            "selectionAllowedWithoutHumanReview": False,
        }
        manifest_path = output / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return manifest
    except Exception:
        for path in output.iterdir():
            path.unlink()
        output.rmdir()
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--identity", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--size", type=int, default=1024)
    args = parser.parse_args()
    if args.size < 512 or args.size > 4096:
        raise SystemExit("size must be between 512 and 4096")
    result = build_hunyuan_multiview_package(
        args.identity.resolve(), args.source_root.resolve(), args.output.resolve(), args.size
    )
    print(json.dumps({"valid": True, "views": len(result["views"]),
                      "missingViews": result["missingViews"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
