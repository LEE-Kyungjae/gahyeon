#!/usr/bin/env python3
"""Build a checksum-bound five-view MetaHuman identity review board."""

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
    path = (owner.parent / uri).resolve()
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"missing or unsafe referenced file: {path}")
    return path


def tile(path: Path, label: str, size=(600, 760)) -> Image.Image:
    source = Image.open(path).convert("RGB")
    image = ImageOps.contain(source, (size[0] - 24, size[1] - 72))
    canvas = Image.new("RGB", size, (49, 51, 56))
    canvas.paste(image, ((size[0] - image.width) // 2, 58 + (size[1] - 70 - image.height) // 2))
    ImageDraw.Draw(canvas).text((14, 18), label, fill=(245, 245, 245), font=ImageFont.load_default())
    return canvas


def build(identity_path: Path, capture_path: Path, board_path: Path) -> dict:
    identity_path, capture_path = identity_path.resolve(), capture_path.resolve()
    identity, capture = load(identity_path), load(capture_path)
    if identity.get("status") != "source-canon" or identity.get("canonicalSource") != "user-provided-originals":
        raise ValueError("user-provided canonical identity manifest required")
    if (capture.get("jobId") != "gahyeon-post-conform-identity-v002"
            or capture.get("editorRuntimeVerified") is not True
            or capture.get("resolution") != [1440, 2560]
            or capture.get("profile") != "looking-glass-go"):
        raise ValueError("real Looking Glass Go post-conform capture required")
    references = {item["index"]: item for item in identity.get("references", [])}
    renders = {item.get("view"): item for item in capture.get("renders", [])}
    if tuple(renders) != tuple(VIEW_TO_CANONICAL):
        raise ValueError("exact ordered five-view capture required")
    rows, evidence = [], []
    for view, index in VIEW_TO_CANONICAL.items():
        reference = references.get(index)
        if not reference or reference.get("identityAuthority") != "canonical":
            raise ValueError(f"canonical reference missing: {index}")
        reference_path = resolve(identity_path, reference["file"])
        if sha256(reference_path) != reference.get("sha256"):
            raise ValueError(f"canonical checksum differs: {index}")
        render = renders[view]
        candidate_path = resolve(capture_path, render.get("uri", ""))
        if sha256(candidate_path) != render.get("sha256"):
            raise ValueError(f"candidate checksum differs: {view}")
        camera = render.get("camera", {})
        if not camera.get("actorPath") or len(camera.get("location", [])) != 3 or len(camera.get("rotation", [])) != 3:
            raise ValueError(f"sealed camera evidence missing: {view}")
        rows.append((tile(reference_path, f"Canonical {index:02d} | {reference['view']}"),
                     tile(candidate_path, f"MetaHuman v002 | {view}")))
        evidence.append({
            "view": view,
            "canonical": {"index": index, "path": str(reference_path), "sha256": sha256(reference_path)},
            "candidate": {"path": str(candidate_path), "sha256": sha256(candidate_path), "camera": camera},
        })
    board = Image.new("RGB", (1200, 760 * 5), (34, 36, 40))
    for row, pair in enumerate(rows):
        board.paste(pair[0], (0, row * 760)); board.paste(pair[1], (600, row * 760))
    board_path.parent.mkdir(parents=True, exist_ok=True)
    board.save(board_path, quality=95)
    return {
        "schemaVersion": 1,
        "kind": "metahuman-v002-five-view-identity-comparison",
        "state": "awaiting-authorized-human-decision",
        "identityManifest": {"path": str(identity_path), "sha256": sha256(identity_path)},
        "captureManifest": {"path": str(capture_path), "sha256": sha256(capture_path)},
        "board": {"path": str(board_path.resolve()), "sha256": sha256(board_path.resolve()), "dimensions": [1200, 3800]},
        "evidence": evidence,
        "limitations": [
            "canonical index 06 is the available three-quarter authority for both 45-degree candidate rows",
            "this board does not create an automated identity score or approval",
        ],
        "identityScore": None,
        "automaticApproval": False,
        "qualityClaim": None,
    }


def verify(manifest_path: Path) -> dict:
    value = load(manifest_path.resolve())
    if (value.get("state") != "awaiting-authorized-human-decision"
            or value.get("identityScore") is not None
            or value.get("automaticApproval") is not False
            or value.get("qualityClaim") is not None):
        raise ValueError("comparison state or claims differ")
    for key in ("identityManifest", "captureManifest", "board"):
        item = value.get(key, {})
        path = Path(item.get("path", ""))
        if not path.is_absolute() or not path.is_file() or path.is_symlink() or sha256(path) != item.get("sha256"):
            raise ValueError(f"comparison lineage differs: {key}")
    if [item.get("view") for item in value.get("evidence", [])] != list(VIEW_TO_CANONICAL):
        raise ValueError("comparison evidence differs")
    with Image.open(value["board"]["path"]) as image:
        if list(image.size) != value["board"].get("dimensions") or image.size != (1200, 3800):
            raise ValueError("comparison board dimensions differ")
    return {"valid": True, "views": 5, "state": value["state"], "automaticApproval": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--identity", type=Path)
    parser.add_argument("--capture", type=Path)
    parser.add_argument("--board", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        result = verify(args.output)
    else:
        if not args.identity or not args.capture or not args.board:
            parser.error("--identity, --capture and --board required")
        if args.output.exists() or args.board.exists():
            raise SystemExit("refusing to overwrite comparison output")
        result = build(args.identity, args.capture, args.board)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"valid": True, "state": result["state"], "views": 5, "qualityClaim": None}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
