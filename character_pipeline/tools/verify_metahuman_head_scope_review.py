#!/usr/bin/env python3
"""Verify named approval of a head/neck/eyes working scene before export."""

from __future__ import annotations

import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path


def digest(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    if not path.is_file() or path.is_symlink(): raise ValueError(f"missing or unsafe file: {path}")
    return json.loads(path.read_text())


def validate(config: dict, review_path: Path, now: datetime | None = None) -> dict:
    review = load(review_path)
    if review.get("schemaVersion") != 1 or review.get("scope") != config["requiredScope"]:
        raise ValueError("head scope review schema or scope differs")
    if review.get("approved") is not True or review.get("automatic") is not False or review.get("productionMeshAllowed") is not False:
        raise ValueError("head scope requires explicit shape-only approval")
    reviewer = review.get("reviewer", {})
    if not reviewer.get("name") or reviewer.get("role") not in config["authorizedReviewerRoles"]:
        raise ValueError("head scope requires an authorized named reviewer")
    reviewed = datetime.fromisoformat(review.get("reviewedAt", "").replace("Z", "+00:00"))
    if reviewed.tzinfo is None or reviewed.astimezone(timezone.utc) > (now or datetime.now(timezone.utc)):
        raise ValueError("head scope review timestamp is invalid")
    scene_record = review.get("workingScene", {}); scene = Path(scene_record.get("path", ""))
    report_record = review.get("preparationReport", {}); report_path = Path(report_record.get("path", ""))
    for label, path, record in (("scene", scene, scene_record), ("report", report_path, report_record)):
        if not path.is_absolute() or path.is_symlink() or not path.is_file() or digest(path) != record.get("sha256"):
            raise ValueError(f"head scope {label} checksum differs")
    report = load(report_path)
    if report.get("output", {}).get("sha256") != digest(scene) or report.get("claim") != "review-required-head-scope-working-scene":
        raise ValueError("head scope scene and preparation report lineage differ")
    views = review.get("views", [])
    if [x.get("view") for x in views] != config["requiredViews"] or any(x.get("verdict") != "acceptable" or not x.get("notes") for x in views):
        raise ValueError("head scope review must accept all five views with notes")
    checks = review.get("checks", [])
    if [x.get("check") for x in checks] != config["requiredChecks"] or any(x.get("passed") is not True or not x.get("notes") for x in checks):
        raise ValueError("head scope review must pass all checks with notes")
    selected = review.get("selectedObjects", [])
    available = {x["name"] for x in report.get("objects", [])}
    if not selected or len(selected) != len(set(selected)) or not set(selected).issubset(available):
        raise ValueError("head scope selected objects are empty, duplicate or unknown")
    return {"valid": True, "scope": review["scope"], "selectedObjects": selected,
            "reviewer": reviewer["name"], "productionMeshAllowed": False}


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("review",type=Path)
    parser.add_argument("--config",type=Path,default=Path("character_pipeline/config/metahuman_head_scope_review.json")); args=parser.parse_args()
    print(json.dumps(validate(load(args.config),args.review.resolve())))
    return 0


if __name__=="__main__": raise SystemExit(main())
