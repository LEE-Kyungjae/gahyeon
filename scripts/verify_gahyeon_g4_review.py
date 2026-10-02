#!/usr/bin/env python3
"""Verify Gahyeon's G4 facial, lip-sync, behavior, and body performance."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import jsonschema

from verify_gahyeon_g3_review import verify as verify_g3


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "docs/contracts/gahyeon-g4-review.schema.json"
REQUIRED_VIEWS = {
    "face-neutral-zero", "expression-happy", "expression-curious", "expression-surprised",
    "expression-sad", "expression-angry", "expression-combination", "viseme-set",
    "korean-lipsync-front", "korean-lipsync-profile", "secondary-blink", "secondary-saccade",
    "secondary-breathing", "secondary-micro-head", "secondary-weight-shift",
    "secondary-fingers", "secondary-shoulders", "lookat-eyes", "lookat-head",
    "state-listening", "state-thinking", "state-speaking", "locomotion-idle",
    "locomotion-walk", "locomotion-sit", "locomotion-talk", "locomotion-foot-slide",
}
REQUIRED_ARTIFACT_ROLES = {"facial-rig", "body-rig", "animation-set"}
REQUIRED_APPROVAL_ROLES = {"facial-reviewer", "animation-reviewer", "audio-reviewer", "operator"}
REQUIRED_VISEMES = {"sil", "aa", "ih", "ou", "ee", "oh", "fv", "l", "mbp", "wq"}
REQUIRED_LAYERS = {"base-locomotion", "posture", "upper-body-gesture", "head", "eyes", "face", "lip-sync", "secondary-motion"}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def local_path(manifest: Path, uri: object) -> Path:
    if not isinstance(uri, str) or not uri.strip() or "://" in uri:
        raise ValueError(f"G4 evidence must use a local relative URI: {uri!r}")
    relative = Path(uri)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"G4 evidence escapes its manifest directory: {uri!r}")
    base = manifest.parent.resolve()
    candidate = (base / relative).resolve()
    if candidate != base and base not in candidate.parents:
        raise ValueError(f"G4 evidence resolves outside its manifest directory: {uri!r}")
    return candidate


def verify_file(manifest: Path, item: dict, *, require_bytes: bool = False) -> Path:
    path = local_path(manifest, item.get("uri"))
    if not path.is_file():
        raise ValueError(f"G4 evidence is missing: {path}")
    if require_bytes and path.stat().st_size != item.get("bytes"):
        raise ValueError(f"G4 artifact byte size mismatch: {path}")
    if digest(path) != item.get("sha256"):
        raise ValueError(f"G4 evidence checksum mismatch: {path}")
    return path


def verify(manifest: Path, *, require_approved: bool = False) -> dict:
    manifest = manifest.resolve()
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()).validate(payload)
    approved = payload["status"] == "approved"
    complete = payload["status"] in {"candidate", "approved"}
    verify_g3(verify_file(manifest, payload["g3Review"]), require_approved=complete)

    artifact_roles = [item["role"] for item in payload["artifacts"]]
    if len(artifact_roles) != len(set(artifact_roles)):
        raise ValueError("G4 review contains duplicate artifact roles")
    for item in payload["artifacts"]:
        verify_file(manifest, item, require_bytes=True)
    views = [item["view"] for item in payload["evidence"]]
    if len(views) != len(set(views)):
        raise ValueError("G4 review contains duplicate semantic views")
    for item in payload["evidence"]:
        verify_file(manifest, item)
    approvals = [item["role"] for item in payload["approvals"]]
    if len(approvals) != len(set(approvals)):
        raise ValueError("G4 review contains duplicate approval roles")

    if require_approved and not approved:
        raise ValueError("G4 review is not approved")
    if complete:
        missing = sorted(REQUIRED_VIEWS - set(views))
        extra = sorted(set(views) - REQUIRED_VIEWS)
        if missing or extra or len(views) != len(REQUIRED_VIEWS):
            raise ValueError(f"Complete G4 evidence mismatch: missing={missing}, extra={extra}")
        if set(artifact_roles) != REQUIRED_ARTIFACT_ROLES:
            raise ValueError("Complete G4 requires facial rig, body rig, and animation set")
        audit = payload["performanceAudit"]
        if set(audit["visemes"]) != REQUIRED_VISEMES:
            raise ValueError("Complete G4 has an incomplete or non-canonical viseme set")
        if set(audit["animationLayers"]) != REQUIRED_LAYERS:
            raise ValueError("Complete G4 must preserve all layered animation responsibilities")
    if approved:
        if set(approvals) != REQUIRED_APPROVAL_ROLES:
            raise ValueError("Approved G4 requires facial, animation, audio, and operator approvals")
        blocking = [item["id"] for item in payload["findings"]
                    if item["severity"] == "blocking" and item["status"] != "resolved"]
        if blocking:
            raise ValueError(f"Approved G4 contains unresolved blocking findings: {blocking}")

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
        print(f"G4 review validation failed: {error}", file=sys.stderr)
        raise SystemExit(2) from None
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
