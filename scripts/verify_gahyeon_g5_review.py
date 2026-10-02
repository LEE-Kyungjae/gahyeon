#!/usr/bin/env python3
"""Verify Gahyeon's G5 visual, latency, resilience, and performance acceptance."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import jsonschema

from verify_gahyeon_g4_review import verify as verify_g4


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "docs/contracts/gahyeon-g5-review.schema.json"
REQUIRED_VIEWS = {
    "desktop-face-closeup", "desktop-waist-conversation", "desktop-fullbody-movement",
    "desktop-side-light", "desktop-backlight", "desktop-expression-lipsync",
    "desktop-groom-motion", "desktop-cloth-collision", "latency-microphone-reflex",
    "latency-stt-first-partial", "latency-behavior-transition", "latency-tts-first-audio",
    "latency-barge-in-cancel", "resilience-backend-off-idle",
    "resilience-reflex-during-cognition", "resilience-desktop-without-looking-glass",
    "resilience-looking-glass-disconnect", "persistence-world-state-restore",
    "performance-frame-trace", "performance-vram-trace", "performance-load-trace",
}
OPTIONAL_VIEWS = {"looking-glass-light-field", "looking-glass-shared-world-state"}
REQUIRED_ARTIFACT_ROLES = {"packaged-build", "telemetry-bundle", "fixed-scene-captures"}
REQUIRED_APPROVAL_ROLES = {"character-quality-reviewer", "runtime-reviewer", "performance-reviewer", "operator"}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def local_path(manifest: Path, uri: object) -> Path:
    if not isinstance(uri, str) or not uri.strip() or "://" in uri:
        raise ValueError(f"G5 evidence must use a local relative URI: {uri!r}")
    relative = Path(uri)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"G5 evidence escapes its manifest directory: {uri!r}")
    base = manifest.parent.resolve()
    candidate = (base / relative).resolve()
    if candidate != base and base not in candidate.parents:
        raise ValueError(f"G5 evidence resolves outside its manifest directory: {uri!r}")
    return candidate


def verify_file(manifest: Path, item: dict, *, require_bytes: bool = False) -> Path:
    path = local_path(manifest, item.get("uri"))
    if not path.is_file():
        raise ValueError(f"G5 evidence is missing: {path}")
    if require_bytes and path.stat().st_size != item.get("bytes"):
        raise ValueError(f"G5 artifact byte size mismatch: {path}")
    if digest(path) != item.get("sha256"):
        raise ValueError(f"G5 evidence checksum mismatch: {path}")
    return path


def verify(manifest: Path, *, require_approved: bool = False) -> dict:
    manifest = manifest.resolve()
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()).validate(payload)
    approved = payload["status"] == "approved"
    complete = payload["status"] in {"candidate", "approved"}
    verify_g4(verify_file(manifest, payload["g4Review"]), require_approved=complete)

    artifact_roles = [item["role"] for item in payload["artifacts"]]
    if len(artifact_roles) != len(set(artifact_roles)):
        raise ValueError("G5 review contains duplicate artifact roles")
    for item in payload["artifacts"]:
        verify_file(manifest, item, require_bytes=True)
    views = [item["view"] for item in payload["evidence"]]
    if len(views) != len(set(views)):
        raise ValueError("G5 review contains duplicate semantic views")
    for item in payload["evidence"]:
        verify_file(manifest, item)
    approvals = [item["role"] for item in payload["approvals"]]
    if len(approvals) != len(set(approvals)):
        raise ValueError("G5 review contains duplicate approval roles")

    if require_approved and not approved:
        raise ValueError("G5 review is not approved")
    if complete:
        missing = sorted(REQUIRED_VIEWS - set(views))
        extra = sorted(set(views) - REQUIRED_VIEWS - OPTIONAL_VIEWS)
        if missing or extra:
            raise ValueError(f"Complete G5 evidence mismatch: missing={missing}, extra={extra}")
        if set(artifact_roles) != REQUIRED_ARTIFACT_ROLES:
            raise ValueError("Complete G5 requires build, telemetry, and fixed-scene artifacts")
        audit = payload["runtimeAudit"]
        machine = audit["testMachine"]
        if "1660 ti" not in machine["gpu"].lower() or machine["vramMiB"] != 6144:
            raise ValueError("G5 lower-bound acceptance must run on the declared GTX 1660 Ti 6 GiB machine")
        if audit["frameTimeP99Ms"] < audit["frameTimeP95Ms"]:
            raise ValueError("G5 frame-time percentiles are inconsistent")
    if approved:
        if set(approvals) != REQUIRED_APPROVAL_ROLES:
            raise ValueError("Approved G5 requires quality, runtime, performance, and operator approvals")
        blocking = [item["id"] for item in payload["findings"]
                    if item["severity"] == "blocking" and item["status"] != "resolved"]
        if blocking:
            raise ValueError(f"Approved G5 contains unresolved blocking findings: {blocking}")

    return {"valid": True, "status": payload["status"], "evidenceCount": len(views),
            "missingRequiredViews": sorted(REQUIRED_VIEWS - set(views))}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--require-approved", action="store_true")
    args = parser.parse_args()
    try:
        result = verify(args.manifest, require_approved=args.require_approved)
    except (ValueError, json.JSONDecodeError, jsonschema.ValidationError, OSError) as error:
        print(f"G5 review validation failed: {error}", file=sys.stderr)
        raise SystemExit(2) from None
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
