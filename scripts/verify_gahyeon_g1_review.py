#!/usr/bin/env python3
"""Verify the evidence and approval boundary for Gahyeon's G1 model gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import jsonschema

from verify_gahyeon_identity_reference import verify as verify_identity
from verify_gahyeon_modeling_input import verify as verify_modeling


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "docs/contracts/gahyeon-g1-review.schema.json"
REQUIRED_VIEWS = {
    "face-neutral-front", "face-neutral-three-quarter-left", "face-neutral-three-quarter-right",
    "face-neutral-left-profile", "face-neutral-right-profile", "body-neutral-front",
    "body-neutral-profile", "body-neutral-rear", "hair-front", "hair-side", "hair-rear",
    "hair-top", "outfit-front", "outfit-side", "outfit-rear",
}
ARTIST_REQUIRED = {
    "body-neutral-rear": "rear-body",
    "hair-rear": "rear-hair",
    "hair-top": "top-hair",
    "outfit-rear": "rear-outfit",
}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def local_path(manifest: Path, uri: object) -> Path:
    if not isinstance(uri, str) or not uri.strip() or "://" in uri:
        raise ValueError(f"G1 evidence must use a local relative URI: {uri!r}")
    relative = Path(uri)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"G1 evidence escapes its manifest directory: {uri!r}")
    base = manifest.parent.resolve()
    candidate = (base / relative).resolve()
    if candidate != base and base not in candidate.parents:
        raise ValueError(f"G1 evidence resolves outside its manifest directory: {uri!r}")
    return candidate


def verify_file(manifest: Path, item: dict, *, require_bytes: bool = False) -> Path:
    path = local_path(manifest, item.get("uri"))
    if not path.is_file():
        raise ValueError(f"G1 evidence is missing: {path}")
    if require_bytes and path.stat().st_size != item.get("bytes"):
        raise ValueError(f"G1 model artifact byte size mismatch: {path}")
    if digest(path) != item.get("sha256"):
        raise ValueError(f"G1 evidence checksum mismatch: {path}")
    return path


def verify(manifest: Path, *, require_approved: bool = False) -> dict:
    manifest = manifest.resolve()
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()).validate(payload)

    sources = payload["sourceManifests"]
    kinds = [item["kind"] for item in sources]
    if sorted(kinds) != ["identity-reference", "modeling-input"]:
        raise ValueError("G1 review must bind exactly one identity and one modeling manifest")
    for source in sources:
        source_path = verify_file(manifest, source)
        if source["kind"] == "identity-reference":
            verify_identity(source_path)
        else:
            verify_modeling(source_path)

    evidence = payload["evidence"]
    views = [item["view"] for item in evidence]
    if len(views) != len(set(views)):
        raise ValueError("G1 review contains duplicate semantic views")
    for item in evidence:
        verify_file(manifest, item)
        region = ARTIST_REQUIRED.get(item["view"])
        if region and item["designAuthority"] != "artist-authored-completion":
            raise ValueError(f"{item['view']} cannot claim canonical observed authority")
        if region and region not in payload["artistAuthoredRegions"]:
            raise ValueError(f"{item['view']} must declare artist-authored region {region}")

    approvals = payload["approvals"]
    roles = [item["role"] for item in approvals]
    if len(roles) != len(set(roles)):
        raise ValueError("G1 review contains duplicate approval roles")

    approved = payload["status"] == "approved"
    complete = payload["status"] in {"candidate", "approved"}
    if require_approved and not approved:
        raise ValueError("G1 review is not approved")
    if complete:
        missing = sorted(REQUIRED_VIEWS - set(views))
        extra = sorted(set(views) - REQUIRED_VIEWS)
        if missing or extra or len(evidence) != len(REQUIRED_VIEWS):
            raise ValueError(f"Complete G1 evidence mismatch: missing={missing}, extra={extra}")
        verify_file(manifest, payload["modelArtifact"], require_bytes=True)
    if approved:
        if set(roles) != {"identity-reviewer", "technical-reviewer", "operator"}:
            raise ValueError("Approved G1 requires identity, technical, and operator approvals")
        blocking = [item["id"] for item in payload["findings"]
                    if item["severity"] == "blocking" and item["status"] != "resolved"]
        if blocking:
            raise ValueError(f"Approved G1 contains unresolved blocking findings: {blocking}")

    return {"valid": True, "status": payload["status"],
            "evidenceCount": len(evidence),
            "missingRequiredViews": sorted(REQUIRED_VIEWS - set(views))}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--require-approved", action="store_true")
    args = parser.parse_args()
    try:
        result = verify(args.manifest, require_approved=args.require_approved)
    except (ValueError, json.JSONDecodeError, jsonschema.ValidationError, OSError) as error:
        print(f"G1 review validation failed: {error}", file=sys.stderr)
        raise SystemExit(2) from None
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
