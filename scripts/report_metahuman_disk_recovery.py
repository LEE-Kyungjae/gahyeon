#!/usr/bin/env python3
"""Read-only disk recovery report for installing UE 5.6 + MetaHuman data."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


GIB = 1024 ** 3


def run(*command: str) -> str:
    try:
        result = subprocess.run(command, text=True, capture_output=True, check=False, timeout=30)
    except subprocess.TimeoutExpired as error:
        return (error.stdout or "").strip()
    return result.stdout.strip()


def size(path: Path) -> int:
    value = run("du", "-sk", str(path))
    return int(value.split()[0]) * 1024 if value else 0


def docker_df() -> list[dict]:
    rows = []
    for line in run("docker", "system", "df", "--format", "{{json .}}").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return rows


def parse_decimal_size(text: str) -> float:
    value = text.split()[0].upper().replace("IB", "B")
    units = (("GB", 1.0), ("MB", 1 / 1024), ("KB", 1 / 1024 ** 2), ("B", 1 / 1024 ** 3))
    for suffix, factor in units:
        if value.endswith(suffix):
            return float(value[:-len(suffix)]) * factor
    return 0.0


def build(workspace: Path) -> dict:
    home = Path.home()
    free = shutil.disk_usage(workspace).free / GIB
    caches = [
        (home / "Library/Caches", "regenerable-app-caches", "medium"),
        (home / ".gradle", "regenerable-build-cache", "low-medium"),
        (home / ".cache", "mixed-model-and-tool-cache", "medium"),
    ]
    cache_rows = [{"path": str(path), "sizeGiB": round(size(path) / GIB, 2),
                   "classification": kind, "risk": risk, "approved": False}
                  for path, kind, risk in caches]
    docker = docker_df()
    reclaim = {row.get("Type"): parse_decimal_size(row.get("Reclaimable", "0B")) for row in docker}
    running = len(run("docker", "ps", "-q").splitlines())
    active_voicebox = bool(run("pgrep", "-f", "build_voicebox_teacher_from_catalog.py"))
    conservative = sum(row["sizeGiB"] for row in cache_rows)
    docker_nonvolume = reclaim.get("Images", 0) + reclaim.get("Build Cache", 0)
    return {
        "schemaVersion": 1,
        "mode": "read-only-no-delete-no-prune",
        "workspace": str(workspace.resolve()),
        "targetFreeGiB": 80,
        "currentFreeGiB": round(free, 2),
        "shortfallGiB": round(max(0, 80 - free), 2),
        "regenerableCaches": cache_rows,
        "regenerableCacheTotalGiB": round(conservative, 2),
        "docker": {
            "runningContainers": running,
            "systemDf": docker,
            "nonVolumeReclaimableGiB": round(docker_nonvolume, 2),
            "volumeReclaimableGiB": round(reclaim.get("Local Volumes", 0), 2),
            "protectVolumes": True,
            "protectRunningContainers": True,
            "physicalReclaimNotGuaranteedUntilDockerRawCompaction": True,
        },
        "protectedProcesses": {"voiceboxDatasetGenerationActive": active_voicebox},
        "scenarios": [
            {"id": "cache-only", "potentialGiB": round(conservative, 2),
             "meetsHeadroom": free + conservative >= 80, "requiresApproval": True},
            {"id": "cache-plus-docker-build-and-unused-images",
             "potentialGiB": round(conservative + docker_nonvolume, 2),
             "meetsHeadroom": free + conservative + docker_nonvolume >= 80,
             "requiresApproval": True, "volumesIncluded": False},
        ],
        "forbiddenWithoutExplicitApproval": [
            "delete caches", "docker builder prune", "docker image prune",
            "docker volume prune", "stop running containers", "stop Voicebox generation",
        ],
        "nextCheckpoint": "after approved cleanup, rerun preflight and require minimumFreeDiskHeadroom=true",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = build(args.workspace)
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
