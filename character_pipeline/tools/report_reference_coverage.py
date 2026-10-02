#!/usr/bin/env python3
"""Map canonical evidence to the controlled ground-truth matrix without inference."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


EXACT_FACE = {
    "front": "front", "left-profile": "left-90", "right-profile": "right-90",
    "high-angle": "slightly-down", "low-angle": "slightly-up",
}
EXACT_BODY = {"front": "front", "left-profile": "left", "right-profile": "right"}


def report(identity_path: Path, requirements_path: Path) -> dict:
    identity = json.loads(identity_path.read_text(encoding="utf-8"))
    requirements = json.loads(requirements_path.read_text(encoding="utf-8"))["required"]
    coverage = {group: {view: [] for view in views} for group, views in requirements.items()}
    ambiguous = []
    for item in identity.get("references", []):
        kind, view = item.get("kind"), item.get("view")
        if kind == "face" and view in EXACT_FACE:
            coverage["face"][EXACT_FACE[view]].append(item["index"])
        elif kind == "full-body" and view in EXACT_BODY:
            coverage["body"][EXACT_BODY[view]].append(item["index"])
        elif kind == "face" and view == "three-quarter":
            ambiguous.append({"index": item["index"], "reason": "three-quarter angle and side are not calibrated"})
        elif kind == "full-body" and view == "three-quarter":
            ambiguous.append({"index": item["index"], "reason": "body three-quarter angle and side are not calibrated"})
        if item.get("index") in {1, 4, 5, 11}:
            ambiguous.append({"index": item["index"], "reason": "expression label is not controlled in identity manifest"})
    missing = {group: [view for view, refs in values.items() if not refs]
               for group, values in coverage.items()}
    counts = {group: sum(bool(refs) for refs in values.values()) for group, values in coverage.items()}
    return {
        "schemaVersion": 1,
        "status": "complete" if not any(missing.values()) else "incomplete",
        "coverage": coverage,
        "coveredCounts": counts,
        "requiredCounts": {key: len(value) for key, value in requirements.items()},
        "missing": missing,
        "ambiguousNotCounted": ambiguous,
        "generationPolicy": "missing views require controlled capture/generation and human identity review; never infer authority",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--identity", type=Path, required=True)
    parser.add_argument("--requirements", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    value = report(args.identity, args.requirements)
    payload = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

