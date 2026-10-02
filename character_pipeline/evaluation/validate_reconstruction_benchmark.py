#!/usr/bin/env python3
"""Validate parity and evidence for TRELLIS.2/Hunyuan3D reconstruction benchmarks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def validate_reconstruction_benchmark(config: dict, status: dict, base: Path) -> dict:
    models = config["models"]
    if config.get("schemaVersion") != 2:
        raise ValueError("unsupported reconstruction benchmark schema")
    if set(models) != {"trellis", "instantmesh"} or set(status.get("models", {})) != set(models):
        raise ValueError("benchmark must contain independent TRELLIS and InstantMesh models")
    rejected = config.get("historicalRejectedBackend", {})
    if rejected.get("model") != "hunyuan" or rejected.get("mayExecuteInKR") is not False:
        raise ValueError("Hunyuan territory rejection must remain explicit")
    expected_seeds = set(config["seedSet"])
    completed = {}
    for model in models:
        record = status["models"][model]
        provenance = (record.get("runner"), record.get("repository"), record.get("revision"), record.get("weightsSha256"))
        candidates = record.get("candidates", [])
        completed[model] = len(candidates)
        if candidates:
            if not all(provenance) or record.get("licenseReviewed") is not True:
                raise ValueError(f"{model} candidates lack pinned provenance/license review")
            seeds = [item.get("seed") for item in candidates]
            if len(seeds) != len(set(seeds)) or set(seeds) != expected_seeds:
                raise ValueError(f"{model} candidate seeds differ from benchmark")
            for candidate in candidates:
                if candidate.get("status") != "validated":
                    raise ValueError(f"{model} candidate is not validated")
                if candidate.get("claim") != "temporary-shape-estimate-not-production-mesh":
                    raise ValueError(f"{model} candidate overclaims topology")
                if set(candidate.get("outputs", {})) != set(config["requiredOutputs"]):
                    raise ValueError(f"{model} candidate outputs are incomplete")
                for uri in candidate["outputs"].values():
                    if not (base / uri).resolve().is_file():
                        raise ValueError(f"missing benchmark output: {model}: {uri}")
    ready = all(completed[model] == config["candidateCountPerModel"] for model in models)
    state = status.get("state")
    if ready and state not in {"validated", "selection-reviewed"}:
        raise ValueError("complete benchmark has invalid state")
    if not ready and state not in {"toolchain-unavailable", "planned", "running", "failed"}:
        raise ValueError("incomplete benchmark overclaims completion")
    selection = status.get("selection")
    if selection is not None:
        if not ready:
            raise ValueError("selection is forbidden before both model benchmarks complete")
        if selection.get("model") not in models or selection.get("seed") not in expected_seeds:
            raise ValueError("selection does not identify a benchmark candidate")
        if selection.get("role") != config["selectionPolicy"]["selectedRole"]:
            raise ValueError("selection overclaims production role")
        if selection.get("automatic") is not False or not selection.get("measurementEvidence") or not selection.get("humanReview"):
            raise ValueError("selection requires measurements and human review")
    if config["selectionPolicy"].get("productionMeshAllowed") is not False:
        raise ValueError("AI reconstruction may not become production mesh")
    return {"valid": True, "state": state, "models": len(models),
            "completedCandidates": sum(completed.values()), "expectedCandidates": 6,
            "selection": selection is not None, "productionMeshAllowed": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("character_pipeline/config/reconstruction_benchmark.json"))
    parser.add_argument("--status", type=Path, default=Path("character_pipeline/iterations/v001/generation/benchmark-status.json"))
    args = parser.parse_args()
    print(json.dumps(validate_reconstruction_benchmark(
        json.loads(args.config.read_text()), json.loads(args.status.read_text()),
        args.status.parent.resolve())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
