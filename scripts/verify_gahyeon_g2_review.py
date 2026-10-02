#!/usr/bin/env python3
"""Verify Gahyeon's G2 sculpt, topology, lookdev, and base-rig review."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import jsonschema

from verify_gahyeon_g1_review import verify as verify_g1


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "docs/contracts/gahyeon-g2-review.schema.json"
REQUIRED_VIEWS = {
    "sculpt-face-front", "sculpt-face-three-quarter-left", "sculpt-face-three-quarter-right",
    "sculpt-face-left-profile", "sculpt-face-right-profile", "sculpt-body-front",
    "sculpt-body-profile", "sculpt-body-rear", "topology-face-neutral", "topology-eyelids",
    "topology-mouth", "topology-body", "eye-assembly", "mouth-interior", "skin-albedo",
    "skin-normal-displacement", "skin-roughness", "rig-eyelid-contact", "rig-lip-seal",
    "rig-jaw-rotation", "rig-cheek-volume",
}
REQUIRED_ARTIFACT_ROLES = {"high-poly-master", "animation-mesh"}
REQUIRED_APPROVAL_ROLES = {"identity-reviewer", "topology-reviewer", "lookdev-reviewer", "operator"}
TECHNICAL_VIEWS = {view for view in REQUIRED_VIEWS if view.startswith(("topology-", "rig-", "skin-"))}
TECHNICAL_VIEWS.update({"eye-assembly", "mouth-interior"})


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def local_path(manifest: Path, uri: object) -> Path:
    if not isinstance(uri, str) or not uri.strip() or "://" in uri:
        raise ValueError(f"G2 evidence must use a local relative URI: {uri!r}")
    relative = Path(uri)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"G2 evidence escapes its manifest directory: {uri!r}")
    base = manifest.parent.resolve()
    candidate = (base / relative).resolve()
    if candidate != base and base not in candidate.parents:
        raise ValueError(f"G2 evidence resolves outside its manifest directory: {uri!r}")
    return candidate


def verify_file(manifest: Path, item: dict, *, require_bytes: bool = False) -> Path:
    path = local_path(manifest, item.get("uri"))
    if not path.is_file():
        raise ValueError(f"G2 evidence is missing: {path}")
    if require_bytes and path.stat().st_size != item.get("bytes"):
        raise ValueError(f"G2 artifact byte size mismatch: {path}")
    if digest(path) != item.get("sha256"):
        raise ValueError(f"G2 evidence checksum mismatch: {path}")
    return path


def verify(manifest: Path, *, require_approved: bool = False) -> dict:
    manifest = manifest.resolve()
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()).validate(payload)
    approved = payload["status"] == "approved"
    complete = payload["status"] in {"candidate", "approved"}

    g1_path = verify_file(manifest, payload["g1Review"])
    verify_g1(g1_path, require_approved=complete)

    roles = [item["role"] for item in payload["artifacts"]]
    if len(roles) != len(set(roles)):
        raise ValueError("G2 review contains duplicate artifact roles")
    for item in payload["artifacts"]:
        verify_file(manifest, item, require_bytes=True)

    views = [item["view"] for item in payload["evidence"]]
    if len(views) != len(set(views)):
        raise ValueError("G2 review contains duplicate semantic views")
    for item in payload["evidence"]:
        verify_file(manifest, item)
        if item["view"] in TECHNICAL_VIEWS and item["authority"] == "g1-derived":
            raise ValueError(f"{item['view']} cannot claim G1-derived implementation authority")

    approvals = [item["role"] for item in payload["approvals"]]
    if len(approvals) != len(set(approvals)):
        raise ValueError("G2 review contains duplicate approval roles")

    if require_approved and not approved:
        raise ValueError("G2 review is not approved")
    if complete:
        missing = sorted(REQUIRED_VIEWS - set(views))
        extra = sorted(set(views) - REQUIRED_VIEWS)
        if missing or extra or len(views) != len(REQUIRED_VIEWS):
            raise ValueError(f"Complete G2 evidence mismatch: missing={missing}, extra={extra}")
        if set(roles) != REQUIRED_ARTIFACT_ROLES:
            raise ValueError("Complete G2 requires high-poly master and animation mesh artifacts")
    if approved:
        if set(approvals) != REQUIRED_APPROVAL_ROLES:
            raise ValueError("Approved G2 requires identity, topology, lookdev, and operator approvals")
        blocking = [item["id"] for item in payload["findings"]
                    if item["severity"] == "blocking" and item["status"] != "resolved"]
        if blocking:
            raise ValueError(f"Approved G2 contains unresolved blocking findings: {blocking}")

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
        print(f"G2 review validation failed: {error}", file=sys.stderr)
        raise SystemExit(2) from None
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
