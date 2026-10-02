#!/usr/bin/env python3
"""Build a canonical-versus-sane-template recovery board without claiming identity."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


VIEW_TO_CANONICAL = {
    "face-front": 3,
    "face-left-45": 6,
    "face-right-45": 6,
    "face-left-profile": 7,
    "face-right-profile": 8,
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"missing or unsafe input: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def resolve(owner: Path, uri: str) -> Path:
    result = (owner.parent / uri).resolve()
    if not result.is_file() or result.is_symlink():
        raise ValueError(f"missing or unsafe evidence: {result}")
    return result


def tile(path: Path, label: str, size=(600, 760)) -> Image.Image:
    with Image.open(path) as source_image:
        source = source_image.convert("RGB")
    image = ImageOps.contain(source, (size[0] - 24, size[1] - 72))
    canvas = Image.new("RGB", size, (45, 47, 52))
    canvas.paste(image, ((size[0] - image.width) // 2, 58 + (size[1] - 70 - image.height) // 2))
    ImageDraw.Draw(canvas).text((14, 18), label, fill=(245, 245, 245), font=ImageFont.load_default())
    return canvas


def build(identity_path: Path, capture_path: Path, board_path: Path) -> dict:
    identity_path = identity_path.resolve()
    capture_path = capture_path.resolve()
    identity = load(identity_path)
    capture = load(capture_path)
    if identity.get("status") != "source-canon" or identity.get("canonicalSource") != "user-provided-originals":
        raise ValueError("user-provided canonical identity required")
    if (capture.get("jobId") != "gahyeon-metahuman-template-baseline-v074"
            or capture.get("state") != "captured-sane-template-baseline"
            or capture.get("editorRuntimeVerified") is not True
            or capture.get("resolution") != [1440, 2560]
            or capture.get("automaticApproval") is not False):
        raise ValueError("real immutable v073 template baseline capture required")
    references = {item["index"]: item for item in identity.get("references", [])}
    renders = {item.get("view"): item for item in capture.get("renders", [])}
    if tuple(renders) != tuple(VIEW_TO_CANONICAL):
        raise ValueError("exact ordered five-view capture required")
    rows = []
    evidence = []
    for view, index in VIEW_TO_CANONICAL.items():
        reference = references[index]
        canonical = resolve(identity_path, reference["file"])
        candidate = resolve(capture_path, renders[view]["uri"])
        if sha256(canonical) != reference["sha256"] or sha256(candidate) != renders[view]["sha256"]:
            raise ValueError(f"evidence checksum differs: {view}")
        rows.append((tile(canonical, f"Canonical {index:02d} | {reference['view']}"),
                     tile(candidate, f"Sane MetaHuman baseline v073 | {view}")))
        evidence.append({"view": view, "canonicalIndex": index,
                         "canonicalSha256": sha256(canonical), "candidateSha256": sha256(candidate)})
    board = Image.new("RGB", (1200, 3800), (34, 36, 40))
    for row, pair in enumerate(rows):
        board.paste(pair[0], (0, row * 760))
        board.paste(pair[1], (600, row * 760))
    board_path.parent.mkdir(parents=True, exist_ok=True)
    board.save(board_path, quality=95)
    return {
        "schemaVersion": 1,
        "iteration": "v074",
        "state": "sane-template-baseline-ready-for-defect-analysis",
        "identityManifest": {"path": str(identity_path), "sha256": sha256(identity_path)},
        "captureManifest": {"path": str(capture_path), "sha256": sha256(capture_path)},
        "board": {"path": str(board_path.resolve()), "sha256": sha256(board_path.resolve()),
                  "dimensions": [1200, 3800]},
        "evidence": evidence,
        "limitations": [
            "the right 45-degree row uses the available canonical index 06 authority",
            "this sane MetaHuman template is a recovery baseline, not a Gahyeon identity candidate",
            "no identity score or approval is inferred",
        ],
        "identityScore": None,
        "automaticApproval": False,
        "productionReady": False,
        "qualityClaim": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--identity", type=Path, required=True)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--board", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.board.exists() or args.output.exists():
        raise SystemExit("refusing to overwrite immutable v073 recovery evidence")
    value = build(args.identity, args.capture, args.board)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"valid": True, "state": value["state"], "views": 5}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
