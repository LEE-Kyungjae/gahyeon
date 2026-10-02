#!/usr/bin/env python3
"""Rank complete reconstruction evidence without selecting or promoting a mesh."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"missing evidence: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _mean_absolute_relative_error(comparison: dict[str, Any], score_key: str) -> float:
    if comparison.get(score_key) is not None:
        raise ValueError(f"comparison fabricates {score_key}")
    values = []
    for item in comparison.get("deltas", []):
        value = item.get("relativeDeltaPercent")
        if not isinstance(value, (int, float)):
            raise ValueError("comparison has missing or non-numeric relative delta")
        values.append(abs(float(value)))
    if not values:
        raise ValueError("comparison contains no deltas")
    return sum(values) / len(values)


def _validate_quality(path: Path, view: str) -> None:
    value = _load(path)
    if value.get("dimensions") != [1440, 2560] or value.get("expectedDimensions") != [1440, 2560]:
        raise ValueError(f"{view} is not Looking Glass Go 1440x2560")
    if value.get("validCapture") is not True or value.get("defects"):
        raise ValueError(f"{view} render quality gate failed")
    if value.get("qualityClaim") is not None:
        raise ValueError(f"{view} render quality report overclaims artistic quality")


def evaluate_candidate(config: dict[str, Any], candidate: Path) -> dict[str, Any]:
    state_path = candidate / "postprocess-state.json"
    state = _load(state_path)
    if (state.get("state") != "completed" or state.get("claim") !=
            "evaluated-temporary-shape-estimate-not-production-mesh" or
            state.get("productionMeshAllowed") is not False):
        raise ValueError(f"candidate postprocess is not complete: {candidate}")
    if state.get("panelResolution") != [1440, 2560] or state.get("views") != config["requiredViews"]:
        raise ValueError(f"candidate uses a different display contract: {candidate}")
    expected = state.get("expected", {})
    for view, quality in zip(config["requiredViews"], expected.get("renderQuality", [])):
        _validate_quality(Path(quality), view)
    if len(expected.get("renderQuality", [])) != len(config["requiredViews"]):
        raise ValueError("candidate render-quality evidence is incomplete")
    face_path, body_path = Path(expected["faceComparison"]), Path(expected["bodyComparison"])
    face_error = _mean_absolute_relative_error(_load(face_path), "identitySimilarityScore")
    body_error = _mean_absolute_relative_error(_load(body_path), "bodySimilarityScore")
    weights = config["weights"]
    weighted_error = face_error * weights["faceGeometry"] + body_error * weights["bodyGeometry"]
    eligible = weighted_error <= config["maximumMeanAbsoluteRelativeErrorPercent"]
    return {
        "candidate": str(candidate), "model": state["model"], "seed": state["seed"],
        "postprocessStateSha256": digest(state_path),
        "measurementErrorsPercent": {"faceGeometryMeanAbsoluteRelative": round(face_error, 6),
                                      "bodyGeometryMeanAbsoluteRelative": round(body_error, 6),
                                      "weighted": round(weighted_error, 6)},
        "eligibleForHumanReview": eligible,
        "claim": "measurement-error-ranking-only-not-identity-or-aaa-score",
        "productionMeshAllowed": False,
    }


def build_shortlist(config: dict[str, Any], candidates: list[Path]) -> dict[str, Any]:
    if (config.get("schemaVersion") != 1 or config.get("displayProfile") != "looking-glass-go" or
            config.get("panelResolution") != [1440, 2560]):
        raise ValueError("shortlist must use Looking Glass Go")
    weights = config.get("weights", {})
    if abs(sum(weights.values()) - 1.0) > 1e-9 or weights.get("faceGeometry", 0) <= weights.get("bodyGeometry", 1):
        raise ValueError("shortlist must prioritize identity-facing geometry")
    if len(candidates) != config["candidateCount"] or len(set(map(str, candidates))) != len(candidates):
        raise ValueError("shortlist requires six distinct candidates")
    records = [evaluate_candidate(config, candidate.resolve()) for candidate in candidates]
    expected = {(model, seed) for model in config["models"] for seed in config["seeds"]}
    actual = {(item["model"], item["seed"]) for item in records}
    if actual != expected or len(actual) != len(records):
        raise ValueError("shortlist candidates do not cover both models and all seeds")
    records.sort(key=lambda item: (not item["eligibleForHumanReview"],
                                   item["measurementErrorsPercent"]["weighted"],
                                   item["model"], item["seed"]))
    for rank, item in enumerate(records, 1):
        item["measurementRank"] = rank
    return {
        "schemaVersion": 1, "state": "awaiting-human-review", "displayProfile": "looking-glass-go",
        "panelResolution": [1440, 2560], "candidates": records,
        "shortlist": [item["candidate"] for item in records if item["eligibleForHumanReview"]],
        "selection": None, "automaticSelection": False, "productionMeshAllowed": False,
        "requiredHumanViews": config["selectionPolicy"]["requiredHumanViews"],
        "limitations": [
            "2D landmark error does not establish identity, depth, topology, deformation or AAA quality",
            "profile and three-quarter likeness require side-by-side human review",
            "the selected reconstruction remains only a shape estimate for MetaHuman conform",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("character_pipeline/config/reconstruction_shortlist.json"))
    parser.add_argument("--candidate", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite: {args.output}")
    result = build_shortlist(_load(args.config), args.candidate)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"valid": True, "state": result["state"], "candidates": len(result["candidates"]),
                      "eligible": len(result["shortlist"]), "selection": None}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
