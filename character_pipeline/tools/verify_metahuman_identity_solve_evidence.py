#!/usr/bin/env python3
"""Verify human-reviewed v002 MetaHuman Identity Solve evidence, fail closed."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROLES = {"character-owner", "character-art-director", "character-technical-artist"}
VIEWS = {"front", "left-profile", "right-profile", "template-a", "template-b"}
CANONICAL = {3, 6, 7, 8}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"missing or unsafe file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def referenced(owner: Path, item: dict) -> Path:
    path = (owner.parent / item.get("uri", "")).resolve()
    if not path.is_file() or path.is_symlink() or sha256(path) != item.get("sha256"):
        raise ValueError(f"evidence file missing or checksum differs: {path}")
    return path


def verify(path: Path) -> dict:
    value = load(path)
    if value.get("schemaVersion") != 1 or value.get("sessionId") != "gahyeon-metahuman-identity-v002":
        raise ValueError("unsupported Identity evidence")
    if value.get("state") != "identity-solved-human-reviewed" or value.get("automatic") is not False:
        raise ValueError("Identity Solve evidence overclaims its state")
    if value.get("productionReady") is not False or value.get("qualityClaim") is not None:
        raise ValueError("Identity evidence cannot claim production quality")
    receipt = value.get("importReceipt", {})
    receipt_path = referenced(path, receipt)
    receipt_value = load(receipt_path)
    if receipt_value.get("state") != "shape-imported-awaiting-guided-identity":
        raise ValueError("import receipt state differs")
    reviewer = value.get("reviewer", {})
    if not str(reviewer.get("name", "")).strip() or reviewer.get("role") not in ROLES:
        raise ValueError("authorized named reviewer required")
    reviewed = datetime.fromisoformat(value.get("reviewedAt", "").replace("Z", "+00:00"))
    if reviewed.tzinfo is None or reviewed.astimezone(timezone.utc) > datetime.now(timezone.utc):
        raise ValueError("review timestamp invalid")
    identity = value.get("identityAsset", {})
    if identity.get("class") != "MetaHumanIdentity" or not str(identity.get("path", "")).startswith("/Game/"):
        raise ValueError("solved MetaHumanIdentity asset missing")
    checks = value.get("checks", {})
    required_checks = {
        "componentsConfiguredFromMesh", "neutralFramePromoted", "neutralFrameTracked",
        "markersHumanCorrected", "identitySolveCompleted", "templateOverlayReviewed",
        "frontIdentityReviewed", "bothProfilesReviewed",
    }
    if any(checks.get(key) is not True for key in required_checks):
        raise ValueError("guided Identity check missing")
    evidence = value.get("evidence", [])
    if len(evidence) != len(VIEWS) or {item.get("view") for item in evidence} != VIEWS:
        raise ValueError("exact front, profiles and template A/B evidence required")
    for item in evidence:
        if item.get("captureType") not in {"viewport-screenshot", "identity-template-overlay"}:
            raise ValueError("unsupported evidence capture type")
        referenced(path, item)
    authority = value.get("canonicalComparison", {})
    if set(authority.get("referenceIndices", [])) != CANONICAL:
        raise ValueError("canonical comparison must use 03/06/07/08")
    if authority.get("identityDecision") not in {"keep-for-conform", "reject-and-resolve"}:
        raise ValueError("explicit human identity decision required")
    if authority.get("identityScore") is not None:
        raise ValueError("unvalidated numeric identity score is forbidden")
    if authority["identityDecision"] == "keep-for-conform" and value.get("blockingFindings"):
        raise ValueError("cannot keep a solve with blocking identity findings")
    if authority["identityDecision"] == "reject-and-resolve":
        return {"valid": True, "state": value["state"], "decision": "reject-and-resolve",
                "conformAllowed": False, "qualityClaim": None}
    return {"valid": True, "state": value["state"], "decision": "keep-for-conform",
            "conformAllowed": True, "qualityClaim": None}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.evidence.resolve())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
