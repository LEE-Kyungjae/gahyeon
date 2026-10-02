#!/usr/bin/env python3
"""Generate a reviewable, network-off-by-default CUDA worker bootstrap plan."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any


SHA = re.compile(r"^[0-9a-f]{40}$")


def validate_bootstrap_manifest(config: dict[str, Any], snapshots: dict[str, Any]) -> dict[str, Any]:
    if config.get("schemaVersion") != 1 or config.get("networkDefault") is not False:
        raise ValueError("bootstrap must default to offline")
    if config.get("productionMeshAllowed") is not False:
        raise ValueError("bootstrap may not produce production topology")
    repositories = config.get("repositories", [])
    if {item.get("id") for item in repositories} != {"trellis", "instantmesh"}:
        raise ValueError("bootstrap repository set incomplete")
    for item in repositories:
        if not SHA.fullmatch(str(item.get("revision", ""))) or not str(item.get("url", "")).startswith("https://github.com/"):
            raise ValueError("repository must use pinned HTTPS provenance")
    trellis = snapshots.get("snapshots", {}).get("trellis", {})
    if not SHA.fullmatch(str(trellis.get("revision", ""))) or not trellis.get("files"):
        raise ValueError("TRELLIS snapshot is not pinned")
    if trellis.get("inputRequirement") != "pre-masked-rgba-png":
        raise ValueError("TRELLIS must require pre-masked RGBA input")
    forbidden = set(config.get("forbiddenModels", []))
    if trellis.get("forbiddenDependency", {}).get("repository") not in forbidden:
        raise ValueError("RMBG dependency rejection missing")
    if "Tencent-Hunyuan/Hunyuan3D-2" not in forbidden:
        raise ValueError("Hunyuan territory rejection missing")
    if trellis.get("gatedDependency", {}).get("approvalRequired") is not True:
        raise ValueError("DINOv3 approval must be explicit")
    return {"valid": True, "repositories": 2,
            "snapshotFiles": sum(len(item.get("files", [])) + sum(len(dep.get("files", [])) for dep in item.get("dependencies", [])) for item in snapshots["snapshots"].values()),
            "networkDefault": False, "productionMeshAllowed": False}


def build_download_commands(config: dict[str, Any], snapshots: dict[str, Any], install_root: Path,
                            cache_root: Path, approvals: set[str], allow_network: bool) -> list[list[str]]:
    validate_bootstrap_manifest(config, snapshots)
    if not allow_network:
        raise ValueError("network access requires explicit opt-in")
    if not install_root.is_absolute() or not cache_root.is_absolute():
        raise ValueError("install and cache roots must be absolute")
    if install_root.exists() and any(install_root.iterdir()):
        raise ValueError("install root must be empty")
    missing = set(config["requiredApprovals"]) - approvals
    if missing:
        raise ValueError(f"missing required approvals: {','.join(sorted(missing))}")
    commands = []
    for repo in config["repositories"]:
        target = install_root / repo["id"]
        clone = ["git", "clone", "--filter=blob:none"]
        if repo.get("recursive"):
            clone.append("--recurse-submodules")
        clone.extend([repo["url"], str(target)])
        commands.extend([clone, ["git", "-C", str(target), "checkout", "--detach", repo["revision"]]])
    for model, snapshot in snapshots["snapshots"].items():
        patterns = list(snapshot.get("allowPatterns", []))
        commands.append(["hf", "download", snapshot["repository"], "--revision", snapshot["revision"],
                         "--local-dir", str(cache_root / model), *sum((["--include", p] for p in patterns), [])])
        for dependency in snapshot.get("dependencies", []):
            commands.append(["hf", "download", dependency["repository"], "--revision", dependency["revision"],
                             "--local-dir", str(cache_root / model / "dependencies" / dependency["repository"].replace("/", "__")),
                             *sum((["--include", item["path"]] for item in dependency["files"]), [])])
    return commands


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("character_pipeline/config/worker_bootstrap.json"))
    parser.add_argument("--snapshots", type=Path, default=Path("character_pipeline/config/worker_handoff.json"))
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    snapshots = json.loads(args.snapshots.read_text())
    print(json.dumps(validate_bootstrap_manifest(config, snapshots)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
