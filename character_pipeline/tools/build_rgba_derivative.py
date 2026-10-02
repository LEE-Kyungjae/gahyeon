#!/usr/bin/env python3
"""Combine canonical RGB with a separately reviewed alpha proposal."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_rgba_derivative(source: Path, alpha_source: Path, output: Path,
                          manifest: Path, canonical_index: int) -> dict:
    for path in (output, manifest):
        if path.exists():
            raise ValueError(f"refusing to overwrite derivative: {path}")
    with Image.open(source) as original, Image.open(alpha_source) as proposal:
        original.load(); proposal.load()
        if original.size != proposal.size:
            raise ValueError("source and alpha proposal dimensions differ")
        rgb = original.convert("RGB")
        alpha = proposal.convert("RGBA").getchannel("A")
        extrema = alpha.getextrema()
        if extrema[0] != 0 or extrema[1] != 255:
            raise ValueError("alpha proposal lacks transparent or opaque pixels")
        rgba = rgb.copy(); rgba.putalpha(alpha)
        output.parent.mkdir(parents=True, exist_ok=True)
        rgba.save(output)
        pixels = alpha.histogram()
        total = original.width * original.height
    record = {
        "schemaVersion": 1, "canonicalIndex": canonical_index, "status": "draft-awaiting-human-review",
        "identityAuthority": "canonical-original-rgb", "alphaAuthority": "ai-proposed-human-review-required",
        "source": {"path": str(source), "sha256": sha256(source)},
        "alphaSource": {"path": str(alpha_source), "sha256": sha256(alpha_source)},
        "derivative": {"path": str(output), "sha256": sha256(output),
                       "width": original.width, "height": original.height, "mode": "RGBA"},
        "coverage": {"transparentFraction": pixels[0] / total,
                     "opaqueFraction": pixels[255] / total,
                     "partialFraction": sum(pixels[1:255]) / total},
        "rgbInvariant": "derivative RGB equals canonical source RGB for every pixel",
        "approved": False, "reviewer": None, "reviewedAt": None,
        "claim": "draft-mask-not-approved-reconstruction-input"
    }
    manifest.write_text(json.dumps(record, indent=2) + "\n")
    return record


def validate_matte_review(record: dict, require_approved: bool = False) -> dict:
    if record.get("status") not in {"draft-awaiting-human-review", "approved"}:
        raise ValueError("invalid matte review status")
    if record.get("identityAuthority") != "canonical-original-rgb" or record.get("alphaAuthority") != "ai-proposed-human-review-required":
        raise ValueError("matte authority is invalid")
    if record.get("rgbInvariant") != "derivative RGB equals canonical source RGB for every pixel":
        raise ValueError("RGB preservation invariant missing")
    approved = record.get("approved") is True
    if approved and (record.get("status") != "approved" or not record.get("reviewer") or not record.get("reviewedAt")):
        raise ValueError("approval lacks reviewer evidence")
    if require_approved and not approved:
        raise ValueError("matte is not human approved")
    return {"valid": True, "canonicalIndex": record["canonicalIndex"], "approved": approved}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--alpha-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--canonical-index", type=int, required=True)
    args = parser.parse_args()
    print(json.dumps(build_rgba_derivative(args.source, args.alpha_source, args.output,
                                           args.manifest, args.canonical_index)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
