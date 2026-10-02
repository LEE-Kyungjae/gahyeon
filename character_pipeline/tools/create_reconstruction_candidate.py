#!/usr/bin/env python3
"""Create a non-overwriting model-specific reconstruction candidate workspace."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import tempfile

from reconstruction_contract import CANDIDATE, validate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--model", choices=("trellis", "instantmesh"), required=True)
    parser.add_argument("--iteration", required=True)
    parser.add_argument("--input-manifest", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    args = parser.parse_args()
    model_root = args.root.resolve() / "generation" / args.model
    model_root.mkdir(parents=True, exist_ok=True)
    numbers = [int(match.group(0).split("_")[1]) for path in model_root.iterdir()
               if path.is_dir() and (match := CANDIDATE.fullmatch(path.name))]
    candidate_id = f"candidate_{max(numbers, default=0) + 1:03d}"
    directory = model_root / candidate_id
    temporary = Path(tempfile.mkdtemp(prefix=f".{candidate_id}-", dir=model_root))
    data = {
        "schemaVersion": 1,
        "characterId": "gahyeon",
        "candidateId": candidate_id,
        "iteration": args.iteration,
        "model": args.model,
        "claim": "temporary-shape-estimate-not-production-mesh",
        "status": "planned",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "seed": args.seed,
        "inputManifest": str(args.input_manifest.resolve()),
        "provenance": {"repository": None, "revision": None, "weightsSha256": None, "runner": None},
        "parameters": {},
        "outputs": [],
        "validation": {"status": "not-run", "defects": []},
        "failure": None
    }
    try:
        for name in ("inputs", "raw", "renders", "measurements", "logs"):
            (temporary / name).mkdir()
        validate(data, directory, verify_files=False)
        manifest = temporary / "candidate.json"
        manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.rename(directory)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    manifest = directory / "candidate.json"
    print(manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
