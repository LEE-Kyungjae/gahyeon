#!/usr/bin/env python3
"""Evaluate hypothesis-driven keep/reject decisions without random tweaking."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def _number(value, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise ValueError(f"invalid numeric value: {name}")
    return float(value)


def evaluate_refinement_decision(config: dict, decision: dict) -> dict:
    result = decision.get("decision")
    if result not in config["decisions"]:
        raise ValueError("invalid refinement decision")
    for key in ("hypothesis", "action", "expectedResult", "actualResult", "rationale"):
        if not isinstance(decision.get(key), str) or not decision[key].strip():
            raise ValueError(f"refinement decision requires {key}")
    parent = decision.get("parent")
    comparisons = decision.get("comparisons", [])
    if result == "baseline":
        if parent is not None or comparisons:
            raise ValueError("baseline may not have a parent or comparisons")
        if decision.get("targetMetrics") or decision.get("guardrailMetrics"):
            raise ValueError("baseline may not claim comparison metrics")
        return {"valid": True, "decision": "baseline", "comparableMetrics": 0,
                "automaticApproval": False}
    if not isinstance(parent, str) or not parent:
        raise ValueError("comparison decision requires parent")
    targets = set(decision.get("targetMetrics", []))
    guardrails = set(decision.get("guardrailMetrics", []))
    if not targets or targets & guardrails:
        raise ValueError("target and guardrail metrics must be nonempty and disjoint")
    names = [item.get("metric") for item in comparisons]
    if len(names) != len(set(names)) or set(names) != targets | guardrails:
        raise ValueError("comparison metrics do not exactly match targets and guardrails")
    meaningful = config["minimumMeaningfulDelta"]
    deltas = {}
    unscored = []
    for item in comparisons:
        before, after = item.get("before"), item.get("after")
        if before is None or after is None:
            unscored.append(item["metric"])
            deltas[item["metric"]] = None
            continue
        delta = _number(after, "after") - _number(before, "before")
        declared = _number(item.get("delta"), "delta")
        if not math.isclose(delta, declared, abs_tol=1e-6):
            raise ValueError(f"declared delta disagrees: {item['metric']}")
        deltas[item["metric"]] = round(delta, 6)
    blocking = decision.get("blockingDefects", [])
    target_improved = bool(targets) and all(deltas[name] is not None and deltas[name] >= meaningful for name in targets)
    target_regressed = any(deltas[name] is not None and deltas[name] <= -meaningful for name in targets)
    guardrail_regressed = any(deltas[name] is not None and deltas[name] <= -meaningful for name in guardrails)
    expected = (
        "inconclusive" if unscored else
        "reject" if target_regressed or guardrail_regressed or blocking else
        "keep" if target_improved else
        "inconclusive"
    )
    if result != expected:
        raise ValueError(f"decision disagrees with evidence: expected {expected}")
    if decision.get("automaticApproval") is not False:
        raise ValueError("refinement decision may not auto-approve")
    return {"valid": True, "decision": result, "comparableMetrics": len(comparisons) - len(unscored),
            "unscoredMetrics": sorted(unscored), "targetImproved": target_improved,
            "targetRegressed": target_regressed, "guardrailRegressed": guardrail_regressed,
            "blockingDefects": len(blocking), "automaticApproval": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("decision", type=Path)
    parser.add_argument("--config", type=Path, default=Path("character_pipeline/config/refinement_decision.json"))
    args = parser.parse_args()
    print(json.dumps(evaluate_refinement_decision(
        json.loads(args.config.read_text()), json.loads(args.decision.read_text()))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
