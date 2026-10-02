#!/usr/bin/env python3
"""Create the next immutable character refinement iteration."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from iteration_contract import SCORE_KEYS, VERSION, validate


def next_version(iterations: Path) -> str:
    numbers = [int(match.group(1)) for item in iterations.iterdir()
               if item.is_dir() and (match := VERSION.fullmatch(item.name))]
    return f"v{max(numbers, default=0) + 1:03d}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--hypothesis", required=True)
    parser.add_argument("--action", required=True)
    parser.add_argument("--expected", required=True)
    parser.add_argument("--parent")
    args = parser.parse_args()
    iterations = args.root.resolve() / "iterations"
    iterations.mkdir(parents=True, exist_ok=True)
    version = next_version(iterations)
    directory = iterations / version
    directory.mkdir()  # deliberately fails if a concurrent writer won
    for name in ("inputs", "generation/trellis", "generation/instantmesh",
                 "blender", "metahuman", "textures", "groom", "clothing",
                 "unreal/renders", "evaluation", "logs"):
        (directory / name).mkdir(parents=True)
    data = {
        "schemaVersion": 1,
        "characterId": "gahyeon",
        "version": version,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "parent": args.parent,
        "state": "planned",
        "hypothesis": {
            "statement": args.hypothesis,
            "action": args.action,
            "expectedResult": args.expected,
        },
        "inputs": [],
        "stages": [],
        "artifacts": [],
        "evaluation": {
            "evaluatorVersion": None,
            "scores": {key: None for key in SCORE_KEYS},
            "defects": [],
            "scoreDeltaFromParent": {key: None for key in SCORE_KEYS},
        },
        "actualResult": None,
        "decision": None,
    }
    validate(data, directory, verify_files=False)
    manifest = directory / "iteration.json"
    manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
