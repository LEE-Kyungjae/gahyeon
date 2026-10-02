#!/usr/bin/env python3
"""Seal a named human review of a P26 shortlist candidate for MetaHuman conform."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"missing or unsafe file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_time(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("review timestamp must include timezone")
    return result.astimezone(timezone.utc)


def seal_selection(config: dict[str, Any], shortlist_path: Path, review_path: Path,
                   now: datetime | None = None) -> dict[str, Any]:
    shortlist, review = _load(shortlist_path), _load(review_path)
    if config.get("schemaVersion") != 1 or review.get("schemaVersion") != 1:
        raise ValueError("unsupported reconstruction review schema")
    if (shortlist.get("state") != "awaiting-human-review" or shortlist.get("selection") is not None or
            shortlist.get("automaticSelection") is not False or shortlist.get("productionMeshAllowed") is not False):
        raise ValueError("shortlist is not awaiting human review")
    if (shortlist.get("displayProfile") != "looking-glass-go" or
            shortlist.get("panelResolution") != [1440, 2560]):
        raise ValueError("shortlist is not bound to Looking Glass Go")
    lineage = review.get("shortlist", {})
    if (Path(lineage.get("path", "")).resolve() != shortlist_path.resolve() or
            lineage.get("sha256") != digest(shortlist_path)):
        raise ValueError("review and shortlist lineage differ")
    if review.get("automatic") is not False or review.get("productionMeshAllowed") is not False:
        raise ValueError("review cannot be automatic or promote production topology")
    reviewer = review.get("reviewer", {})
    if (not reviewer.get("name") or reviewer.get("role") not in config["authorizedReviewerRoles"]):
        raise ValueError("selection requires an authorized named reviewer")
    reviewed_at = _parse_time(review.get("reviewedAt", ""))
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if reviewed_at > now:
        raise ValueError("review timestamp is in the future")
    candidate_path = Path(review.get("selectedCandidate", "")).resolve()
    records = {Path(item["candidate"]).resolve(): item for item in shortlist.get("candidates", [])}
    candidate_record = records.get(candidate_path)
    if candidate_record is None or not candidate_record.get("eligibleForHumanReview"):
        raise ValueError("selected candidate is not eligible in the shortlist")
    if candidate_record.get("productionMeshAllowed") is not False:
        raise ValueError("candidate record overclaims production topology")
    state_path = candidate_path / "postprocess-state.json"
    state = _load(state_path)
    if digest(state_path) != candidate_record.get("postprocessStateSha256"):
        raise ValueError("selected candidate changed after shortlist")
    if state.get("state") != "completed" or state.get("productionMeshAllowed") is not False:
        raise ValueError("selected candidate postprocess is not complete")
    reviews = review.get("views", [])
    if ([item.get("view") for item in reviews] != config["requiredViews"] or
            any(item.get("verdict") not in config["allowedVerdicts"] or not item.get("notes") for item in reviews)):
        raise ValueError("review must cover all nine views in contract order with notes")
    if any(item["verdict"] == "blocking" for item in reviews):
        raise ValueError("blocking view finding forbids selection")
    criteria = review.get("criteria", [])
    if ([item.get("criterion") for item in criteria] != config["requiredCriteria"] or
            any(item.get("verdict") not in config["allowedVerdicts"] or not item.get("notes") for item in criteria)):
        raise ValueError("review must cover every required identity criterion")
    if any(item["verdict"] == "blocking" for item in criteria):
        raise ValueError("blocking identity criterion forbids selection")
    raw_mesh = Path(state["commands"][0]["argv"][state["commands"][0]["argv"].index("--input") + 1])
    if not raw_mesh.is_file():
        raise ValueError("selected raw reconstruction mesh is missing")
    return {
        "schemaVersion": 1, "state": "selection-reviewed", "reviewedAt": reviewed_at.isoformat(),
        "reviewer": reviewer, "displayProfile": "looking-glass-go", "panelResolution": [1440, 2560],
        "shortlist": {"path": str(shortlist_path.resolve()), "sha256": digest(shortlist_path)},
        "selected": {"candidate": str(candidate_path), "model": candidate_record["model"],
                     "seed": candidate_record["seed"], "postprocessStateSha256": digest(state_path),
                     "rawMesh": {"path": str(raw_mesh.resolve()), "sha256": digest(raw_mesh)},
                     "measurementRank": candidate_record["measurementRank"],
                     "role": config["selectedRole"]},
        "viewReviewCount": len(reviews), "criterionReviewCount": len(criteria),
        "automatic": False, "productionMeshAllowed": False,
        "nextStage": "metahuman-identity-conform-input",
        "limitations": ["human review does not validate topology, deformation, materials or AAA quality",
                        "the selected mesh is shape reference only and must not ship"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("character_pipeline/config/reconstruction_human_review.json"))
    parser.add_argument("--shortlist", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite: {args.output}")
    result = seal_selection(_load(args.config), args.shortlist.resolve(), args.review.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"valid": True, "state": result["state"], "model": result["selected"]["model"],
                      "seed": result["selected"]["seed"], "productionMeshAllowed": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
