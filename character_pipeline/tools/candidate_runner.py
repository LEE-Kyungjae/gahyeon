#!/usr/bin/env python3
"""Atomic runner boundary shared by reconstruction backends."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from typing import Any, Callable

from PIL import Image
from character_pipeline.tools.shape_input_approval import validate_shape_input_approval


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def validate_runner_request(contract: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    if contract.get("schemaVersion") != 1 or request.get("schemaVersion") != 1:
        raise ValueError("unsupported runner schema")
    if request.get("model") not in contract["models"] or request.get("seed") not in contract["allowedSeeds"]:
        raise ValueError("model or seed is outside benchmark contract")
    if request.get("claim") != contract["claim"] or request.get("productionMeshAllowed") is not False:
        raise ValueError("runner request overclaims production topology")
    input_path = Path(request.get("input", {}).get("path", ""))
    if not input_path.is_absolute() or not input_path.is_file() or input_path.is_symlink():
        raise ValueError("runner input must be an absolute regular file")
    if sha256(input_path) != request["input"].get("sha256"):
        raise ValueError("runner input checksum differs")
    with Image.open(input_path) as image:
        image.load()
        rules = contract["input"]
        if image.format != "PNG" or image.mode != rules["mode"]:
            raise ValueError("runner input must be RGBA PNG")
        if image.width < rules["minimumWidth"] or image.height < rules["minimumHeight"]:
            raise ValueError("runner input is below minimum resolution")
        alpha = image.getchannel("A")
        extrema = alpha.getextrema()
        if rules["requireTransparentPixel"] and extrema[0] == 255:
            raise ValueError("runner input has no transparent background")
    if rules.get("requireHumanScopeApproval"):
        approval_path = Path(request["input"].get("approval", ""))
        if not approval_path.is_absolute() or not approval_path.is_file() or approval_path.is_symlink():
            raise ValueError("runner input approval package missing")
        approval = json.loads(approval_path.read_text())
        approval_config = json.loads(Path(request["input"].get("approvalConfig", "")).read_text())
        approved = validate_shape_input_approval(approval_config, approval)
        if approval.get("derivative", {}).get("sha256") != request["input"]["sha256"]:
            raise ValueError("runner input and approval checksum differ")
    snapshot = request.get("snapshot", {})
    if not snapshot.get("revision") or not snapshot.get("inventorySha256"):
        raise ValueError("runner snapshot provenance incomplete")
    candidate = Path(request.get("candidate", ""))
    if not candidate.is_absolute() or not candidate.is_dir():
        raise ValueError("candidate directory must already exist")
    manifest = candidate / "candidate.json"
    if (candidate / "raw" / "result.json").exists():
        raise ValueError("candidate already contains a promoted result")
    data = json.loads(manifest.read_text())
    if data.get("status") != "planned" or data.get("model") != request["model"] or data.get("seed") != request["seed"]:
        raise ValueError("candidate manifest differs from runner request")
    return {"valid": True, "model": request["model"], "seed": request["seed"],
            "inputSha256": request["input"]["sha256"]}


def execute_candidate(contract: dict[str, Any], request: dict[str, Any],
                      backend: Callable[[dict[str, Any], Path], dict[str, Any]]) -> dict[str, Any]:
    validate_runner_request(contract, request)
    candidate = Path(request["candidate"])
    raw = candidate / "raw"
    manifest = candidate / "candidate.json"
    temporary = Path(tempfile.mkdtemp(prefix=".runner-", dir=candidate))
    try:
        result = backend(request, temporary)
        meshes = [path for path in temporary.iterdir()
                  if path.is_file() and path.suffix.lower().lstrip(".") in contract["output"]["formats"]]
        if len(meshes) != contract["output"]["exactMeshCount"]:
            raise ValueError("backend must emit exactly one allowed mesh")
        mesh = meshes[0]
        if mesh.stat().st_size < contract["output"]["minimumBytes"]:
            raise ValueError("backend mesh is implausibly small")
        if result.get("seed") != request["seed"] or result.get("model") != request["model"]:
            raise ValueError("backend result provenance differs")
        receipt = {"schemaVersion": 1, "model": request["model"], "seed": request["seed"],
                   "inputSha256": request["input"]["sha256"], "snapshot": request["snapshot"],
                   "mesh": {"file": mesh.name, "bytes": mesh.stat().st_size, "sha256": sha256(mesh)},
                   "backend": result, "completedAt": datetime.now(timezone.utc).isoformat(),
                   "claim": contract["claim"], "productionMeshAllowed": False}
        (temporary / "result.json").write_text(json.dumps(receipt, indent=2) + "\n")
        if any(raw.iterdir()):
            raise ValueError("raw output directory is not empty")
        raw.rmdir()
        temporary.rename(raw)
        candidate_data = json.loads(manifest.read_text())
        candidate_data["status"] = "generated"
        candidate_data["provenance"] = {
            "repository": request["snapshot"].get("repository", "pinned-worker-snapshot"),
            "revision": request["snapshot"]["revision"],
            "weightsSha256": request["snapshot"]["inventorySha256"],
            "runner": request.get("runner", f"{request['model']}-atomic-runner"),
        }
        candidate_data["outputs"] = [
            {"role": "raw-mesh", "uri": f"raw/{mesh.name}",
             "bytes": receipt["mesh"]["bytes"], "sha256": receipt["mesh"]["sha256"]},
            {"role": "runner-receipt", "uri": "raw/result.json",
             "bytes": (raw / "result.json").stat().st_size,
             "sha256": sha256(raw / "result.json")},
        ]
        replacement = candidate / ".candidate.json.next"
        replacement.write_text(json.dumps(candidate_data, indent=2) + "\n")
        replacement.replace(manifest)
        return receipt
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
