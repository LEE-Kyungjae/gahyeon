#!/usr/bin/env python3
"""Atomically register immutable evidence in a G1-G5 review."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

import jsonschema

from verify_gahyeon_g1_review import verify as verify_g1
from verify_gahyeon_g2_review import verify as verify_g2
from verify_gahyeon_g3_review import verify as verify_g3
from verify_gahyeon_g4_review import verify as verify_g4
from verify_gahyeon_g5_review import verify as verify_g5


VERIFIERS = {"G1": verify_g1, "G2": verify_g2, "G3": verify_g3,
             "G4": verify_g4, "G5": verify_g5}
AUTHORITY_FIELDS = {"G1": "designAuthority", "G2": "authority"}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def record(review: Path, *, view: str, capture_type: str, evidence_file: Path,
           authority: str | None = None, notes: str | None = None) -> dict:
    if review.is_symlink():
        raise ValueError("review manifest cannot be a symbolic link")
    review = review.resolve()
    if not review.is_file():
        raise ValueError(f"review manifest is missing: {review}")
    payload = json.loads(review.read_text(encoding="utf-8"))
    gate = payload.get("gate")
    verifier = VERIFIERS.get(gate)
    if verifier is None:
        raise ValueError(f"unsupported review gate: {gate!r}")
    if payload.get("status") not in {"draft", "candidate"}:
        raise ValueError(f"evidence cannot modify a {payload.get('status')} review")
    if not isinstance(view, str) or not view.strip():
        raise ValueError("evidence view is required")
    if any(item.get("view") == view for item in payload.get("evidence", [])):
        raise ValueError(f"review already contains evidence for {view}")

    if evidence_file.is_symlink():
        raise ValueError("evidence file cannot be a symbolic link")
    evidence_file = evidence_file.resolve()
    if not evidence_file.is_file() or evidence_file == review:
        raise ValueError(f"evidence file is missing or invalid: {evidence_file}")
    workspace = review.parent.resolve()
    try:
        relative = evidence_file.relative_to(workspace)
    except ValueError as error:
        raise ValueError("evidence file must stay inside the review workspace") from error

    authority_field = AUTHORITY_FIELDS.get(gate)
    if authority_field and not authority:
        raise ValueError(f"{gate} evidence requires --authority")
    if not authority_field and authority is not None:
        raise ValueError(f"{gate} evidence does not accept --authority")
    item = {"view": view, "captureType": capture_type,
            "uri": relative.as_posix(), "sha256": digest(evidence_file)}
    if authority_field:
        item[authority_field] = authority
    if notes:
        item["notes"] = notes
    payload["evidence"].append(item)

    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=workspace,
                prefix=f".{review.stem}.", suffix=".json", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        verifier(temporary)
        os.chmod(temporary, review.stat().st_mode & 0o777)
        os.replace(temporary, review)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return item


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--view", required=True)
    parser.add_argument("--capture-type", required=True)
    parser.add_argument("--file", required=True, type=Path)
    parser.add_argument("--authority")
    parser.add_argument("--notes")
    args = parser.parse_args()
    try:
        item = record(args.review, view=args.view, capture_type=args.capture_type,
                      evidence_file=args.file, authority=args.authority, notes=args.notes)
    except (ValueError, OSError, json.JSONDecodeError, jsonschema.ValidationError) as error:
        print(f"Quality evidence registration failed: {error}", file=sys.stderr)
        raise SystemExit(2) from None
    print(json.dumps({"recorded": True, **item}, ensure_ascii=False))


if __name__ == "__main__":
    main()
