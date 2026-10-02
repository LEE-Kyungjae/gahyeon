#!/usr/bin/env python3
"""Fail-closed preflight and argv builder for reconstruction workers."""

from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any, Callable


SHA = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def local_capabilities(run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run) -> dict[str, Any]:
    nvidia = shutil.which("nvidia-smi")
    vram = 0
    if nvidia:
        result = run([nvidia, "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                     capture_output=True, text=True, check=False)
        if result.returncode == 0:
            values = [int(value.strip()) for value in result.stdout.splitlines() if value.strip().isdigit()]
            vram = max(values, default=0) / 1024
    return {"os": platform.system().lower(), "architecture": platform.machine().lower(),
            "nvidiaCuda": bool(nvidia), "maximumVramGiB": round(vram, 2)}


def validate_toolchain_preflight(config: dict[str, Any], capabilities: dict[str, Any]) -> dict[str, Any]:
    if config.get("schemaVersion") != 2 or config.get("executionRegion") != "KR":
        raise ValueError("toolchain region/schema must be explicit")
    if config.get("policy", {}).get("shell") is not False or config["policy"].get("productionMeshAllowed") is not False:
        raise ValueError("unsafe execution policy")
    results = {}
    rejected = config.get("historicalRejectedBackend", {})
    if rejected.get("model") != "hunyuan" or rejected.get("mayExecuteInKR") is not False:
        raise ValueError("Hunyuan territory rejection must remain explicit")
    for model in ("trellis", "instantmesh"):
        item = config.get("models", {}).get(model, {})
        blockers = []
        if not SHA.fullmatch(str(item.get("revision", ""))):
            blockers.append("unpinned-revision")
        if not item.get("licenseReviewed"):
            blockers.append("license-review-incomplete")
        if not SHA256.fullmatch(str(item.get("weightsSha256", ""))):
            blockers.append("weights-checksum-missing")
        territory = item.get("territory")
        if territory and (config["executionRegion"] in territory.get("excluded", []) or
                          territory.get("executionAllowed") is False):
            blockers.append("license-territory-forbids-execution")
        requirements = item.get("requirements", {})
        if capabilities.get("os") != requirements.get("os"):
            blockers.append("unsupported-operating-system")
        if requirements.get("accelerator") == "nvidia-cuda" and not capabilities.get("nvidiaCuda"):
            blockers.append("nvidia-cuda-unavailable")
        if capabilities.get("maximumVramGiB", 0) < requirements.get("minimumVramGiB", 0):
            blockers.append("insufficient-vram")
        if not item.get("runner"):
            blockers.append("runner-unavailable")
        results[model] = {"ready": not blockers, "blockers": blockers,
                          "productionMeshAllowed": False}
    return {"valid": True, "state": "ready" if all(v["ready"] for v in results.values()) else "blocked",
            "executionRegion": config["executionRegion"], "capabilities": capabilities, "models": results}


def build_generation_command(config: dict[str, Any], model: str, candidate: Path,
                             input_image: Path, seed: int) -> list[str]:
    item = config.get("models", {}).get(model)
    if not item:
        raise ValueError("unsupported reconstruction model")
    preflight = validate_toolchain_preflight(config, local_capabilities())
    if not preflight["models"][model]["ready"]:
        raise ValueError(f"{model} toolchain blocked: {','.join(preflight['models'][model]['blockers'])}")
    if not candidate.is_absolute() or not input_image.is_absolute():
        raise ValueError("candidate and input paths must be absolute")
    return ["python3", item["runner"], "--repository", item["repository"],
            "--revision", item["revision"], "--weights", item["weights"],
            "--weights-sha256", item["weightsSha256"], "--candidate", str(candidate),
            "--input", str(input_image), "--seed", str(seed)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("character_pipeline/config/reconstruction_toolchains.json"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    report = validate_toolchain_preflight(config, local_capabilities())
    value = json.dumps(report, indent=2) + "\n"
    if args.output:
        if args.output.exists():
            raise SystemExit(f"refusing to overwrite preflight: {args.output}")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(value, encoding="utf-8")
    print(json.dumps(report))
    return 0 if report["state"] == "ready" else 3


if __name__ == "__main__":
    raise SystemExit(main())
