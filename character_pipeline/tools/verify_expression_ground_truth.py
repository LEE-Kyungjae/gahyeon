#!/usr/bin/env python3
"""Fail-closed validator for human-reviewed expression ground truth."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_expression_ground_truth(contract: dict, source_root: Path) -> dict:
    required = contract.get("requirements", [])
    if len(required) != 16 or len(required) != len(set(required)):
        raise ValueError("expression contract must contain 16 unique requirements")
    observations = contract.get("observations", [])
    labels = [item.get("label") for item in observations]
    if len(labels) != len(set(labels)) or not set(labels).issubset(required):
        raise ValueError("observations must have unique required labels")
    for item in observations:
        path = source_root / item["file"]
        if not path.is_file() or digest(path) != item.get("sha256"):
            raise ValueError(f"missing or changed expression source: {item.get('file')}")
        if item.get("authority") not in {"canonical", "supporting"}:
            raise ValueError("expression authority must be canonical or supporting")
        if not item.get("humanObservation") or not item.get("allowedUses"):
            raise ValueError("every expression observation needs human evidence and allowed uses")
    missing = contract.get("missing", [])
    if set(missing) != set(required) - set(labels):
        raise ValueError("missing labels must exactly complement observed labels")
    if contract.get("status") != ("complete" if not missing else "incomplete"):
        raise ValueError("status disagrees with coverage")
    qa = contract.get("displayQA", {})
    if qa.get("profile") != "looking-glass-go" or qa.get("singleViewResolution") != [1440, 2560]:
        raise ValueError("expression QA must target Looking Glass Go 1440x2560")
    if qa.get("quiltRequiresConnectedCalibration") is not True:
        raise ValueError("quilt capture must require connected calibration")
    policy = contract.get("authorityPolicy", {})
    if policy.get("landmarkMetricsAreEvidenceNotLabels") is not True:
        raise ValueError("landmark metrics may not assign expression authority")
    return {"valid": True, "covered": len(labels), "required": len(required), "missing": len(missing),
            "displayProfile": "looking-glass-go"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("contract", type=Path)
    parser.add_argument("--source-root", type=Path, default=Path("artifacts/gahyeon-ch"))
    args = parser.parse_args()
    value = json.loads(args.contract.read_text(encoding="utf-8"))
    print(json.dumps(validate_expression_ground_truth(value, args.source_root), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
