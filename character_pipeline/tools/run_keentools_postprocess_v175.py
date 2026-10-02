#!/usr/bin/env python3
"""Audit and render a downloaded v175 KeenTools head without overwriting it."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps


WORKSPACE = Path("/Users/ze/work/gahyeonbot")
ITERATION = WORKSPACE / "artifacts/gahyeon-ch/iterations/v175-keentools-cloud-multiview"
ITERATION_LABEL = "v175"
MODEL = ITERATION / "gahyeon-keentools-cloud-v175.glb"
IDENTITY = WORKSPACE / "artifacts/gahyeon-ch/identity-reference.json"
BLENDER = Path("/Applications/Blender.app/Contents/MacOS/Blender")
NORMALIZER = WORKSPACE / "character_pipeline/blender/scripts/cleanup_reconstruction_candidate.py"
QA_SETUP = WORKSPACE / "character_pipeline/blender/scripts/setup_reconstruction_qa_scene.py"
RENDERER = WORKSPACE / "character_pipeline/blender/scripts/render_fixed_baseline.py"
VIEWS = ("face-front", "face-left-45", "face-right-45", "face-left-profile",
         "face-right-profile")
CANONICAL = {
    "face-front": 3,
    "face-left-45": 6,
    "face-right-45": 11,
    "face-left-profile": 7,
    "face-right-profile": 8,
}


def digest_postprocess_v175(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command_plan_v175() -> list[list[str]]:
    normalized = ITERATION / f"postprocess/gahyeon-keentools-cloud-{ITERATION_LABEL}-normalized.blend"
    audit = ITERATION / "postprocess/geometry-audit.json"
    qa_scene = ITERATION / f"postprocess/gahyeon-keentools-cloud-{ITERATION_LABEL}-qa.blend"
    renders = ITERATION / "postprocess/renders"
    return [
        [str(BLENDER), "--background", "--factory-startup", "--python", str(NORMALIZER),
         "--", "--input", str(MODEL), "--output", str(normalized), "--report", str(audit),
         "--target-height-cm", "40.0", "--merge-distance-cm", "0.0",
         "--forward=-Y", "--up=+Z"],
        [str(BLENDER), "--background", str(normalized), "--python", str(QA_SETUP),
         "--", "--output", str(qa_scene)],
        [str(BLENDER), "--background", str(qa_scene), "--python", str(RENDERER),
         "--", "--output-dir", str(renders), "--width", "1440", "--height", "2560",
         *[item for view in VIEWS for item in ("--view", view)]],
    ]


def tile_v175(path: Path, label: str, size: tuple[int, int] = (600, 760)) -> Image.Image:
    source = Image.open(path).convert("RGB")
    image = ImageOps.contain(source, (size[0] - 24, size[1] - 72))
    canvas = Image.new("RGB", size, (45, 47, 52))
    canvas.paste(image, ((size[0] - image.width) // 2,
                         58 + (size[1] - 70 - image.height) // 2))
    ImageDraw.Draw(canvas).text((14, 18), label, fill=(245, 245, 245),
                                font=ImageFont.load_default())
    return canvas


def build_identity_board_v175() -> dict[str, Any]:
    render_manifest_path = ITERATION / "postprocess/renders/render-manifest.json"
    identity = json.loads(IDENTITY.read_text(encoding="utf-8"))
    render_manifest = json.loads(render_manifest_path.read_text(encoding="utf-8"))
    if identity.get("status") != "source-canon":
        raise RuntimeError("canonical identity manifest required")
    if render_manifest.get("resolution") != [1440, 2560]:
        raise RuntimeError("Looking Glass Go render resolution required")
    references = {record["index"]: record for record in identity["references"]}
    renders = {record["view"]: record for record in render_manifest["views"]}
    rows = []
    evidence = []
    for view in VIEWS:
        reference = references[CANONICAL[view]]
        reference_path = IDENTITY.parent / reference["file"]
        render_path = render_manifest_path.parent / renders[view]["uri"]
        if digest_postprocess_v175(reference_path) != reference["sha256"]:
            raise RuntimeError(f"canonical checksum differs: {view}")
        if digest_postprocess_v175(render_path) != renders[view]["sha256"]:
            raise RuntimeError(f"render checksum differs: {view}")
        rows.append((tile_v175(reference_path, f"Canonical {CANONICAL[view]:02d} | {view}"),
                     tile_v175(render_path, f"KeenTools {ITERATION_LABEL} | {view}")))
        evidence.append({
            "view": view,
            "canonical": {"path": str(reference_path), "sha256": reference["sha256"]},
            "candidate": {"path": str(render_path), "sha256": renders[view]["sha256"]},
        })
    board_path = ITERATION / "postprocess/identity-review-board.png"
    report_path = ITERATION / "postprocess/identity-review.json"
    if board_path.exists() or report_path.exists():
        raise RuntimeError(f"refusing to overwrite {ITERATION_LABEL} identity review")
    board = Image.new("RGB", (1200, 760 * len(rows)), (30, 32, 36))
    for row, pair in enumerate(rows):
        board.paste(pair[0], (0, row * 760))
        board.paste(pair[1], (600, row * 760))
    board.save(board_path)
    payload = {
        "schemaVersion": 1,
        "iteration": ITERATION_LABEL,
        "status": "awaiting-visual-identity-review",
        "displayProfile": "looking-glass-go-single-view",
        "resolution": [1440, 2560],
        "board": {"path": str(board_path), "sha256": digest_postprocess_v175(board_path)},
        "evidence": evidence,
        "identityApproved": False,
        "metaHumanConformAllowed": False,
        "automaticApproval": False,
    }
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    return payload


def run_keentools_postprocess_v175(dry_run: bool = False) -> dict[str, Any]:
    commands = command_plan_v175()
    if dry_run:
        return {"iteration": ITERATION_LABEL, "dryRun": True, "commands": commands}
    if not MODEL.is_file():
        raise RuntimeError(f"downloaded KeenTools GLB is missing: {MODEL}")
    postprocess = ITERATION / "postprocess"
    if postprocess.exists():
        raise RuntimeError(f"refusing to overwrite immutable postprocess: {postprocess}")
    expected_outputs = (
        (postprocess / f"gahyeon-keentools-cloud-{ITERATION_LABEL}-normalized.blend",
         postprocess / "geometry-audit.json"),
        (postprocess / f"gahyeon-keentools-cloud-{ITERATION_LABEL}-qa.blend",),
        (postprocess / "renders/render-manifest.json",),
    )
    for command, expected in zip(commands, expected_outputs):
        subprocess.run(command, cwd=WORKSPACE, check=True)
        missing = [str(path) for path in expected if not path.is_file()]
        if missing:
            raise RuntimeError(f"Blender stage returned without required outputs: {missing}")
    return build_identity_board_v175()


def main_v175() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run_keentools_postprocess_v175(args.dry_run), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main_v175())
    except (RuntimeError, subprocess.CalledProcessError) as error:
        raise SystemExit(f"ERROR: {error}")
