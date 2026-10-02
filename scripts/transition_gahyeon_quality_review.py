#!/usr/bin/env python3
"""Perform a one-way, verifier-enforced quality review lifecycle transition."""

from __future__ import annotations

import argparse
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
ALLOWED = {("draft", "candidate"), ("draft", "rejected"),
           ("candidate", "approved"), ("candidate", "rejected")}


def transition(review: Path, target: str) -> dict:
    if review.is_symlink():
        raise ValueError("review manifest cannot be a symbolic link")
    review = review.resolve()
    payload = json.loads(review.read_text(encoding="utf-8"))
    verifier = VERIFIERS.get(payload.get("gate"))
    if verifier is None:
        raise ValueError(f"unsupported review gate: {payload.get('gate')!r}")
    current = payload.get("status")
    if (current, target) not in ALLOWED:
        raise ValueError(f"quality review transition is not allowed: {current} -> {target}")
    if target == "rejected" and not payload.get("findings"):
        raise ValueError("rejected review must contain at least one documented finding")
    payload["status"] = target

    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=review.parent,
                                         prefix=f".{review.stem}.", suffix=".json",
                                         delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        verifier(temporary, require_approved=(target == "approved"))
        os.chmod(temporary, review.stat().st_mode & 0o777)
        os.replace(temporary, review)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {"gate": payload["gate"], "from": current, "to": target}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--to", required=True, choices=["candidate", "approved", "rejected"])
    args = parser.parse_args()
    try:
        result = transition(args.review, args.to)
    except (ValueError, OSError, json.JSONDecodeError, jsonschema.ValidationError) as error:
        print(f"Quality review transition failed: {error}", file=sys.stderr)
        raise SystemExit(2) from None
    print(json.dumps({"transitioned": True, **result}, ensure_ascii=False))


if __name__ == "__main__":
    main()
