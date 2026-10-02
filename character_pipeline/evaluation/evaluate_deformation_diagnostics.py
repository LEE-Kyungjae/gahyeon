#!/usr/bin/env python3
"""Evaluate exact frame-level MetaHuman deformation diagnostics."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def evaluate_deformation_diagnostics(config: dict, cases: dict, report: dict) -> dict:
    if report.get("state") != "candidate" or report.get("editorRuntimeVerified") is not True:
        raise ValueError("Editor deformation diagnostics are not a candidate")
    expected = {(case["id"], frame) for case in cases["requiredCases"] for frame in case["frames"]}
    samples = report.get("samples", [])
    actual = {(item.get("case"), item.get("frame")) for item in samples}
    if len(actual) != len(samples):
        raise ValueError("duplicate deformation diagnostic sample")
    if actual != expected:
        raise ValueError(f"deformation frame coverage mismatch: expected={len(expected)} actual={len(actual)}")
    diagnostic_contract = config["diagnostics"]
    failures = []
    maxima = {name: None for name in diagnostic_contract}
    for sample in samples:
        values = sample.get("diagnostics", {})
        if set(values) != set(diagnostic_contract):
            raise ValueError(f"diagnostic keys incomplete: {sample.get('case')}:{sample.get('frame')}")
        for name, contract in diagnostic_contract.items():
            item = values[name]
            value = item.get("value")
            if item.get("unit") != contract["unit"]:
                raise ValueError(f"diagnostic unit mismatch: {name}")
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0:
                raise ValueError(f"invalid diagnostic value: {name}")
            maxima[name] = value if maxima[name] is None else max(maxima[name], value)
            if value > contract["maximum"]:
                failures.append({"case": sample["case"], "frame": sample["frame"],
                                 "diagnostic": name, "value": value,
                                 "maximum": contract["maximum"], "unit": contract["unit"]})
    declared = report.get("summary", {})
    if declared.get("sampleCount") != len(samples) or declared.get("failedSampleCount") != len(failures):
        raise ValueError("declared deformation summary disagrees with samples")
    if failures:
        raise ValueError(f"deformation thresholds exceeded: {len(failures)}")
    if config["samplePolicy"].get("automaticApproval") is not False:
        raise ValueError("deformation diagnostics may not auto-approve")
    return {"valid": True, "samples": len(samples), "cases": len(cases["requiredCases"]),
            "diagnostics": len(diagnostic_contract), "maxima": maxima,
            "automaticApproval": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("character_pipeline/config/deformation_diagnostics.json"))
    parser.add_argument("--cases", type=Path, default=Path("character_pipeline/config/deformation_qa.json"))
    parser.add_argument("--report", type=Path, default=Path("character_pipeline/metahuman/validation/v001/deformation-diagnostics.json"))
    args = parser.parse_args()
    result = evaluate_deformation_diagnostics(
        json.loads(args.config.read_text()), json.loads(args.cases.read_text()),
        json.loads(args.report.read_text()))
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
