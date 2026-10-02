#!/usr/bin/env python3
"""Build and verify the early v002 post-conform identity checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image


VIEWS = ("face-front", "face-left-45", "face-right-45", "face-left-profile", "face-right-profile")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"missing or unsafe input: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def resolve(owner: Path, uri: str) -> Path:
    path = (owner.parent / uri).resolve()
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"missing or unsafe evidence: {path}")
    return path


def build_job(conform_receipt: Path, output_dir: Path) -> dict:
    conform_receipt = conform_receipt.resolve()
    receipt = load(conform_receipt)
    if (receipt.get("state") != "conformed-head-awaiting-production-systems"
            or receipt.get("result") != "SUCCESS" or receipt.get("headConformed") is not True):
        raise ValueError("successful v002 head conform receipt required")
    if receipt.get("productionReady") is not False or receipt.get("qualityClaim") is not None:
        raise ValueError("conform receipt overclaims quality")
    return {
        "schemaVersion": 1,
        "jobId": "gahyeon-post-conform-identity-v002",
        "state": "ready-for-head-only-identity-capture",
        "conformReceipt": {"path": str(conform_receipt), "sha256": sha256(conform_receipt)},
        "characterAsset": receipt["characterAsset"],
        "profile": "looking-glass-go",
        "resolution": [1440, 2560],
        "background": "neutral-mid-gray",
        "views": list(VIEWS),
        "outputDirectory": str(output_dir.resolve()),
        "quilt": {"viewCount": 66, "requiresConnectedCalibration": True},
        "headOnlyCheckpoint": True,
        "requiresGroom": False,
        "requiresFinalSkin": False,
        "automaticApproval": False,
        "qualityClaim": None,
    }


def verify_capture(manifest_path: Path) -> dict:
    manifest = load(manifest_path)
    if manifest.get("jobId") != "gahyeon-post-conform-identity-v002":
        raise ValueError("wrong post-conform capture")
    if manifest.get("profile") != "looking-glass-go" or manifest.get("resolution") != [1440, 2560]:
        raise ValueError("capture is not bound to Looking Glass Go")
    if manifest.get("background") != "neutral-mid-gray" or manifest.get("qualityClaim") is not None:
        raise ValueError("capture presentation or claim differs")
    if manifest.get("editorRuntimeVerified") is not True or manifest.get("headOnlyCheckpoint") is not True:
        raise ValueError("capture lacks real Editor head-only evidence")
    job_item = manifest.get("job", {})
    job_path = Path(job_item.get("path", ""))
    if (not job_path.is_absolute() or not job_path.is_file() or job_path.is_symlink()
            or sha256(job_path) != job_item.get("sha256")):
        raise ValueError("capture job lineage differs")
    job = load(job_path)
    if job.get("state") != "ready-for-head-only-identity-capture" or job.get("views") != list(VIEWS):
        raise ValueError("capture job contract differs")
    entries = manifest.get("renders", [])
    if len(entries) != 5 or tuple(item.get("view") for item in entries) != VIEWS:
        raise ValueError("exact ordered five-view capture required")
    for item in entries:
        camera = item.get("camera", {})
        if (not camera.get("actorPath") or len(camera.get("location", [])) != 3
                or len(camera.get("rotation", [])) != 3
                or not isinstance(camera.get("focalLengthMm"), (int, float))
                or camera["focalLengthMm"] < 50 or camera["focalLengthMm"] > 120):
            raise ValueError(f"sealed camera evidence missing: {item.get('view')}")
        image_path = resolve(manifest_path, item.get("uri", ""))
        if sha256(image_path) != item.get("sha256"):
            raise ValueError(f"capture checksum differs: {item.get('view')}")
        with Image.open(image_path) as image:
            if image.size != (1440, 2560):
                raise ValueError(f"capture resolution differs: {item.get('view')}")
    return {"valid": True, "views": 5, "displayProfile": "looking-glass-go", "qualityClaim": None}


def verify_decision(decision_path: Path) -> dict:
    decision = load(decision_path)
    capture = decision.get("captureManifest", {})
    capture_path = resolve(decision_path, capture.get("uri", ""))
    if sha256(capture_path) != capture.get("sha256"):
        raise ValueError("capture manifest checksum differs")
    verify_capture(capture_path)
    if decision.get("state") != "post-conform-identity-human-reviewed":
        raise ValueError("post-conform identity review missing")
    reviewer = decision.get("reviewer", {})
    if not reviewer.get("name") or reviewer.get("role") not in {
        "character-owner", "character-art-director", "character-technical-artist"
    }:
        raise ValueError("authorized named reviewer required")
    comparison = decision.get("comparison", {})
    if set(comparison.get("canonicalIndices", [])) != {3, 6, 7, 8}:
        raise ValueError("canonical 03/06/07/08 comparison required")
    if comparison.get("identityScore") is not None:
        raise ValueError("unvalidated identity score forbidden")
    outcome = comparison.get("decision")
    if outcome not in {"keep-and-build-surfaces", "reject-and-resolve-identity"}:
        raise ValueError("explicit keep/reject decision required")
    findings = decision.get("blockingFindings", [])
    if outcome == "keep-and-build-surfaces" and findings:
        raise ValueError("cannot keep a conform with blocking identity findings")
    return {"valid": True, "decision": outcome,
            "surfaceWorkAllowed": outcome == "keep-and-build-surfaces", "qualityClaim": None}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--conform-receipt", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify-capture", action="store_true")
    parser.add_argument("--verify-decision", action="store_true")
    args = parser.parse_args()
    if args.verify_capture:
        result = verify_capture(args.output.resolve())
    elif args.verify_decision:
        result = verify_decision(args.output.resolve())
    else:
        if not args.conform_receipt or not args.output_dir:
            parser.error("--conform-receipt and --output-dir required")
        if args.output.exists():
            raise SystemExit(f"refusing to overwrite: {args.output}")
        result = build_job(args.conform_receipt, args.output_dir)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
