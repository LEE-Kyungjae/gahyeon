#!/usr/bin/env python3
"""Atomically add or disposition a finding on a mutable quality review."""

from __future__ import annotations

import argparse
import json
import os
import re
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
MUTABLE_STATUSES = {"draft", "candidate"}
SEVERITIES = {"blocking", "major", "minor", "note"}
DISPOSITIONS = {"resolved", "accepted-risk"}


def _load(review: Path) -> tuple[Path, dict, object]:
    if review.is_symlink():
        raise ValueError("review manifest cannot be a symbolic link")
    review = review.resolve()
    payload = json.loads(review.read_text(encoding="utf-8"))
    verifier = VERIFIERS.get(payload.get("gate"))
    if verifier is None:
        raise ValueError(f"unsupported review gate: {payload.get('gate')!r}")
    if payload.get("status") not in MUTABLE_STATUSES:
        raise ValueError("findings can only be changed on draft or candidate reviews")
    return review, payload, verifier


def _write_verified(review: Path, payload: dict, verifier: object) -> None:
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=review.parent,
                                         prefix=f".{review.stem}.", suffix=".json",
                                         delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        verifier(temporary)  # type: ignore[operator]
        os.chmod(temporary, review.stat().st_mode & 0o777)
        os.replace(temporary, review)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def add_finding(review: Path, *, severity: str, summary: str,
                finding_id: str | None = None) -> dict:
    review, payload, verifier = _load(review)
    if severity not in SEVERITIES:
        raise ValueError(f"unsupported finding severity: {severity}")
    summary = summary.strip()
    if not summary:
        raise ValueError("finding summary is required")
    findings = payload.setdefault("findings", [])
    existing = {item["id"] for item in findings}
    gate = payload["gate"]
    if finding_id is None:
        numbers = [int(match.group(1)) for item in existing
                   if (match := re.fullmatch(rf"{gate}-(\d{{3}})", item))]
        next_number = max(numbers, default=0) + 1
        if next_number > 999:
            raise ValueError(f"{gate} finding identifier space is exhausted")
        finding_id = f"{gate}-{next_number:03d}"
    if finding_id in existing:
        raise ValueError(f"review already contains finding {finding_id}")
    item = {"id": finding_id, "severity": severity, "summary": summary, "status": "open"}
    findings.append(item)
    _write_verified(review, payload, verifier)
    return item


def disposition_finding(review: Path, *, finding_id: str, status: str) -> dict:
    review, payload, verifier = _load(review)
    if status not in DISPOSITIONS:
        raise ValueError(f"unsupported finding disposition: {status}")
    matches = [item for item in payload.get("findings", []) if item.get("id") == finding_id]
    if len(matches) != 1:
        raise ValueError(f"finding {finding_id} does not exist exactly once")
    item = matches[0]
    if item.get("status") != "open":
        raise ValueError(f"finding {finding_id} is already {item.get('status')}")
    if item.get("severity") == "blocking" and status == "accepted-risk":
        raise ValueError("blocking findings must be resolved; risk acceptance is not allowed")
    item["status"] = status
    _write_verified(review, payload, verifier)
    return item


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", required=True, type=Path)
    actions = parser.add_subparsers(dest="action", required=True)
    add = actions.add_parser("add")
    add.add_argument("--severity", required=True, choices=sorted(SEVERITIES))
    add.add_argument("--summary", required=True)
    add.add_argument("--id")
    disposition = actions.add_parser("disposition")
    disposition.add_argument("--id", required=True)
    disposition.add_argument("--status", required=True, choices=sorted(DISPOSITIONS))
    args = parser.parse_args()
    try:
        if args.action == "add":
            item = add_finding(args.review, severity=args.severity,
                               summary=args.summary, finding_id=args.id)
        else:
            item = disposition_finding(args.review, finding_id=args.id, status=args.status)
    except (ValueError, OSError, json.JSONDecodeError, jsonschema.ValidationError) as error:
        print(f"Quality finding update failed: {error}", file=sys.stderr)
        raise SystemExit(2) from None
    print(json.dumps({"updated": True, **item}, ensure_ascii=False))


if __name__ == "__main__":
    main()
