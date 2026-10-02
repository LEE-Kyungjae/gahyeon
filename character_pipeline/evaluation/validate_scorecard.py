#!/usr/bin/env python3
"""Validate evidence-backed scorecards without manufacturing missing quality scores."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_evidence_scorecard(config: dict, scorecard: dict, base: Path) -> dict:
    components = config["components"]
    records = scorecard.get("components", {})
    if set(records) != set(components):
        raise ValueError("scorecard components are incomplete")
    weights = config["weights"]
    if set(weights) != set(components) or not math.isclose(sum(weights.values()), 1.0, abs_tol=1e-9):
        raise ValueError("scorecard weights must cover components and sum to one")
    for name, record in records.items():
        status = record.get("status")
        score = record.get("score")
        if status not in config["statuses"]:
            raise ValueError(f"invalid component status: {name}")
        if status == "scored":
            if not isinstance(score, (int, float)) or isinstance(score, bool) or not 0 <= score <= 100:
                raise ValueError(f"scored component lacks valid score: {name}")
        elif score is not None:
            raise ValueError(f"unscored component carries a number: {name}")
        if record.get("confidence") not in config["confidenceLevels"]:
            raise ValueError(f"invalid confidence: {name}")
        if not record.get("evidence"):
            raise ValueError(f"component lacks evidence references: {name}")
        for evidence in record["evidence"]:
            uri = evidence.get("uri") if isinstance(evidence, dict) else evidence
            if not isinstance(uri, str) or not uri:
                raise ValueError(f"invalid component evidence reference: {name}")
            path = (base / uri).resolve()
            if not path.is_file():
                raise ValueError(f"missing component evidence: {name}: {uri}")
            if status == "scored":
                if not isinstance(evidence, dict) or digest(path) != evidence.get("sha256"):
                    raise ValueError(f"scored component evidence lacks checksum: {name}")
                receipt_uri = evidence.get("verifierReceipt")
                if not isinstance(receipt_uri, str) or not receipt_uri:
                    raise ValueError(f"scored component lacks verifier receipt: {name}")
                receipt_path = (base / receipt_uri).resolve()
                if not receipt_path.is_file() or receipt_path.is_symlink():
                    raise ValueError(f"scored component verifier receipt missing: {name}")
                receipt = json.loads(receipt_path.read_text())
                if (receipt.get("valid") is not True or receipt.get("component") != name
                        or receipt.get("iteration") != scorecard.get("iteration")
                        or receipt.get("evidenceSha256") != evidence["sha256"]
                        or receipt.get("automaticApproval") is not False):
                    raise ValueError(f"scored component verifier receipt differs: {name}")
        for defect in record.get("defects", []):
            for key in ("summary", "likelyCause", "recommendedModification", "confidence", "reviewMode", "severity"):
                if not defect.get(key):
                    raise ValueError(f"defect field missing: {name}.{key}")
            if defect["reviewMode"] not in {"automated", "manual", "automated-then-manual"}:
                raise ValueError(f"invalid defect review mode: {name}")
    all_scored = all(record["status"] == "scored" for record in records.values())
    blocking = sum(
        1 for record in records.values() for defect in record.get("defects", [])
        if defect["severity"] == "blocking"
    )
    expected_overall = (
        round(sum(records[name]["score"] * weights[name] for name in components), 3)
        if all_scored and blocking == 0 else None
    )
    if scorecard.get("overall") != expected_overall:
        raise ValueError("overall score disagrees with evidence availability or weights")
    if scorecard.get("automaticApproval") is not False:
        raise ValueError("scorecard may not auto-approve")
    return {"valid": True, "components": len(components),
            "scored": sum(record["status"] == "scored" for record in records.values()),
            "measuredNotScored": sum(record["status"] == "measured-not-scored" for record in records.values()),
            "unverified": sum(record["status"] == "unverified" for record in records.values()),
            "blockingDefects": blocking, "overall": expected_overall}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("scorecard", type=Path)
    parser.add_argument("--config", type=Path, default=Path("character_pipeline/config/scorecard.json"))
    args = parser.parse_args()
    print(json.dumps(validate_evidence_scorecard(
        json.loads(args.config.read_text()), json.loads(args.scorecard.read_text()),
        args.scorecard.parent.resolve())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
