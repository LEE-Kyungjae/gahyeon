#!/usr/bin/env python3
"""Create and verify non-portable CUDA worker evidence without copying model blobs."""

from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any


SHA = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def validate_worker_handoff(config: dict[str, Any], handoff: dict[str, Any],
                            cache_root: Path | None = None, verify_files: bool = False) -> dict[str, Any]:
    if config.get("schemaVersion") != 1 or handoff.get("schemaVersion") != 1:
        raise ValueError("unsupported worker handoff schema")
    if handoff.get("executionRegion") != config.get("executionRegion"):
        raise ValueError("worker execution region differs")
    if handoff.get("productionMeshAllowed") is not False:
        raise ValueError("worker may not emit production topology")
    capabilities = handoff.get("capabilities", {})
    if capabilities.get("os") != "linux" or capabilities.get("nvidiaCuda") is not True:
        raise ValueError("worker requires Linux and NVIDIA CUDA")
    if capabilities.get("freeDiskGiB", 0) < config["minimumFreeDiskGiB"]:
        raise ValueError("worker free disk below threshold")
    records = handoff.get("models", {})
    if set(records) != set(config["requiredModels"]):
        raise ValueError("worker model evidence incomplete")
    ready = True
    total_files = 0
    for model in config["requiredModels"]:
        expected = config["snapshots"][model]
        record = records[model]
        blockers = record.get("blockers", [])
        gated = expected.get("gatedDependency")
        if gated and gated.get("approvalRequired") is True:
            approval = record.get("licenseApproval")
            if not isinstance(approval, dict) or approval.get("repository") != gated["repository"] or not approval.get("acceptedBy") or not approval.get("acceptedAt"):
                if "gated-license-approval-missing" not in blockers:
                    raise ValueError("gated dependency approval evidence missing")
        if model == "trellis" and not expected.get("revision"):
            if blockers != ["official-weight-snapshot-unpinned"] or record.get("ready") is not False:
                raise ValueError("TRELLIS missing snapshot must fail closed")
            ready = False
            continue
        if record.get("repository") != expected["repository"] or record.get("revision") != expected["revision"]:
            raise ValueError(f"{model} snapshot provenance differs")
        actual_files = record.get("files", [])
        if len(actual_files) != len(expected["files"]):
            raise ValueError(f"{model} snapshot inventory incomplete")
        by_path = {item.get("path"): item for item in actual_files}
        if set(by_path) != {item["path"] for item in expected["files"]}:
            raise ValueError(f"{model} contains non-allowlisted or missing files")
        for item in expected["files"]:
            actual = by_path[item["path"]]
            if actual.get("bytes") != item["bytes"] or actual.get("sha256") != item["sha256"]:
                raise ValueError(f"{model} snapshot checksum or size differs: {item['path']}")
            if verify_files:
                if cache_root is None:
                    raise ValueError("cache root required for file verification")
                path = (cache_root / model / item["path"])
                if config.get("forbidSymlinks") and path.is_symlink():
                    raise ValueError("snapshot symlinks are forbidden")
                if not path.is_file() or path.stat().st_size != item["bytes"] or digest(path) != item["sha256"]:
                    raise ValueError(f"materialized snapshot differs: {item['path']}")
            total_files += 1
        if blockers or record.get("ready") is not True:
            ready = False
    state = "ready" if ready else "blocked"
    if handoff.get("state") != state:
        raise ValueError("worker handoff state overclaims readiness")
    return {"valid": True, "state": state, "models": len(records),
            "verifiedSnapshotFiles": total_files, "productionMeshAllowed": False}


def build_worker_handoff(config: dict[str, Any], capabilities: dict[str, Any],
                         approvals: dict[str, dict[str, str]] | None = None) -> dict[str, Any]:
    approvals = approvals or {}
    models = {}
    for model in config["requiredModels"]:
        snapshot = config["snapshots"][model]
        if not snapshot.get("revision"):
            models[model] = {"ready": False, "repository": snapshot["repository"],
                             "revision": None, "files": [],
                             "blockers": ["official-weight-snapshot-unpinned"]}
        else:
            models[model] = {"ready": True, "repository": snapshot["repository"],
                             "revision": snapshot["revision"], "files": copy.deepcopy(snapshot["files"]),
                             "blockers": []}
            gated = snapshot.get("gatedDependency")
            if gated and gated.get("approvalRequired") is True:
                approval = approvals.get(gated["repository"])
                if approval:
                    models[model]["licenseApproval"] = {"repository": gated["repository"], **approval}
                else:
                    models[model]["ready"] = False
                    models[model]["blockers"].append("gated-license-approval-missing")
    hardware_ready = capabilities.get("os") == "linux" and capabilities.get("nvidiaCuda") is True and capabilities.get("freeDiskGiB", 0) >= config["minimumFreeDiskGiB"]
    if not hardware_ready:
        for record in models.values():
            record["ready"] = False
            if "worker-capabilities-insufficient" not in record["blockers"]:
                record["blockers"].append("worker-capabilities-insufficient")
    return {"schemaVersion": 1, "observedAt": datetime.now(timezone.utc).isoformat(),
            "executionRegion": config["executionRegion"], "state": "ready" if all(r["ready"] for r in models.values()) else "blocked",
            "capabilities": capabilities, "models": models, "productionMeshAllowed": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("character_pipeline/config/worker_handoff.json"))
    parser.add_argument("handoff", type=Path)
    parser.add_argument("--cache-root", type=Path)
    parser.add_argument("--verify-files", action="store_true")
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    handoff = json.loads(args.handoff.read_text())
    print(json.dumps(validate_worker_handoff(config, handoff, args.cache_root, args.verify_files)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
