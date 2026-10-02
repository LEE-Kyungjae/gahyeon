#!/usr/bin/env python3
"""Validate the reproducible, non-promoting expression generation job."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED = {
    "angry", "sad", "eyes-closed", "viseme-sil", "viseme-aa", "viseme-ih",
    "viseme-ou", "viseme-ee", "viseme-oh", "viseme-fv", "viseme-l", "viseme-mbp", "viseme-wq",
}


def validate_expression_capture_job(value: dict) -> dict:
    if value.get("state") not in {"ready", "toolchain-unavailable", "running", "completed", "failed"}:
        raise ValueError("invalid capture job state")
    generator = value.get("generator", {})
    if generator.get("loraSha256") != "8ceb5048b52e400c0ea0525efe76bcd641880317e0f44ec932650110a0dae084":
        raise ValueError("capture job is not pinned to selected LoRA")
    capture = value.get("capture", {})
    if capture.get("width") != 1024 or capture.get("height") != 1024:
        raise ValueError("source expression captures must be square 1024")
    targets = value.get("targets", [])
    labels = {item.get("label") for item in targets}
    seeds = [item.get("seed") for item in targets]
    if labels != REQUIRED or len(seeds) != len(set(seeds)) or not all(isinstance(seed, int) for seed in seeds):
        raise ValueError("capture targets or deterministic seeds are incomplete")
    if not all(item.get("prompt") for item in targets):
        raise ValueError("every target needs an explicit deformation hypothesis prompt")
    policy = value.get("outputPolicy", {})
    if policy.get("initialAuthority") != "candidate" or policy.get("automaticPromotion") is not False:
        raise ValueError("generated expressions may not become authority automatically")
    if policy.get("neverOverwrite") is not True or policy.get("recordSha256") is not True:
        raise ValueError("capture outputs must be immutable and checksummed")
    return {"valid": True, "targets": len(targets), "state": value["state"], "automaticPromotion": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("job", type=Path)
    args = parser.parse_args()
    print(json.dumps(validate_expression_capture_job(json.loads(args.job.read_text(encoding="utf-8")))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
