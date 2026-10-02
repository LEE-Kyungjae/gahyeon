#!/usr/bin/env python3
"""Build a checksum-bound canonical-versus-clay board for v178."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path("/Users/ze/work/gahyeonbot")
ITERATION = ROOT / "artifacts/gahyeon-ch/iterations/v178-keentools-cloud-equal-shape"
IDENTITY = ROOT / "artifacts/gahyeon-ch/identity-reference.json"
RENDERS = ITERATION / "postprocess/clay-renders-attempt-003"
VIEWS = {
    "face-front": 3,
    "face-left-45": 6,
    "face-right-45": 11,
    "face-left-profile": 7,
    "face-right-profile": 8,
}


def sha256_v178(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tile_v178(path: Path, label: str, size: tuple[int, int] = (600, 760)) -> Image.Image:
    image = ImageOps.contain(Image.open(path).convert("RGB"), (size[0] - 24, size[1] - 72))
    canvas = Image.new("RGB", size, (38, 40, 44))
    canvas.paste(image, ((size[0] - image.width) // 2,
                         58 + (size[1] - 70 - image.height) // 2))
    ImageDraw.Draw(canvas).text((14, 18), label, fill=(245, 245, 245),
                                font=ImageFont.load_default())
    return canvas


def build_clay_identity_board_v178() -> dict:
    identity = json.loads(IDENTITY.read_text(encoding="utf-8"))
    manifest_path = RENDERS / "render-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    references = {item["index"]: item for item in identity["references"]}
    renders = {item["view"]: item for item in manifest["views"]}
    rows = []
    evidence = []
    for view, index in VIEWS.items():
        reference = references[index]
        reference_path = IDENTITY.parent / reference["file"]
        render_path = RENDERS / renders[view]["uri"]
        if sha256_v178(reference_path) != reference["sha256"]:
            raise RuntimeError(f"canonical checksum differs: {index}")
        if sha256_v178(render_path) != renders[view]["sha256"]:
            raise RuntimeError(f"render checksum differs: {view}")
        rows.append((tile_v178(reference_path, f"Canonical {index:02d} | {view}"),
                     tile_v178(render_path, f"KeenTools v178 clay | {view}")))
        evidence.append({"view": view, "canonical": str(reference_path),
                         "candidate": str(render_path)})
    output = ITERATION / "postprocess/clay-identity-review-board.png"
    report = ITERATION / "postprocess/clay-identity-review.json"
    if output.exists() or report.exists():
        raise RuntimeError("refusing to overwrite immutable v178 clay review")
    board = Image.new("RGB", (1200, len(rows) * 760), (30, 32, 36))
    for row, pair in enumerate(rows):
        board.paste(pair[0], (0, row * 760))
        board.paste(pair[1], (600, row * 760))
    board.save(output)
    payload = {"schemaVersion": 1, "iteration": "v178", "status": "awaiting-visual-review",
               "board": {"path": str(output), "sha256": sha256_v178(output)},
               "evidence": evidence, "identityApproved": False,
               "metaHumanConformAllowed": False, "automaticApproval": False}
    report.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(build_clay_identity_board_v178(), ensure_ascii=False))
