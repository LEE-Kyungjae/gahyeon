#!/usr/bin/env python3
"""Atomically seal a model, rig, groom, animation, or runtime artifact into a review."""

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


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def record(review: Path, *, artifact_file: Path, artifact_format: str,
           role: str | None = None) -> dict:
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
        raise ValueError(f"artifact cannot modify a {payload.get('status')} review")

    if artifact_file.is_symlink():
        raise ValueError("artifact file cannot be a symbolic link")
    artifact_file = artifact_file.resolve()
    if not artifact_file.is_file() or artifact_file == review:
        raise ValueError(f"artifact file is missing or invalid: {artifact_file}")
    workspace = review.parent.resolve()
    try:
        relative = artifact_file.relative_to(workspace)
    except ValueError as error:
        raise ValueError("artifact file must stay inside the review workspace") from error

    item = {"format": artifact_format, "uri": relative.as_posix(),
            "sha256": digest(artifact_file), "bytes": artifact_file.stat().st_size}
    if gate == "G1":
        if role is not None:
            raise ValueError("G1 modelArtifact does not accept --role")
        if "modelArtifact" in payload:
            raise ValueError("G1 review already contains a modelArtifact")
        payload["modelArtifact"] = item
    else:
        if not role:
            raise ValueError(f"{gate} artifact requires --role")
        if any(existing.get("role") == role for existing in payload.get("artifacts", [])):
            raise ValueError(f"{gate} review already contains artifact role {role}")
        item = {"role": role, **item}
        payload["artifacts"].append(item)

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
    parser.add_argument("--file", required=True, type=Path)
    parser.add_argument("--format", required=True, dest="artifact_format")
    parser.add_argument("--role")
    args = parser.parse_args()
    try:
        item = record(args.review, artifact_file=args.file,
                      artifact_format=args.artifact_format, role=args.role)
    except (ValueError, OSError, json.JSONDecodeError, jsonschema.ValidationError) as error:
        print(f"Quality artifact registration failed: {error}", file=sys.stderr)
        raise SystemExit(2) from None
    print(json.dumps({"recorded": True, **item}, ensure_ascii=False))


if __name__ == "__main__":
    main()
