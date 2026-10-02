#!/usr/bin/env python3
"""Common fail-closed contract for independent reconstruction candidates."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re


CANDIDATE = re.compile(r"^candidate_[0-9]{3,}$")
MODELS = {"trellis", "instantmesh"}


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def validate(data: dict, directory: Path, verify_files: bool = True) -> dict:
    if data.get("schemaVersion") != 1 or data.get("characterId") != "gahyeon":
        raise ValueError("invalid reconstruction identity/schema")
    if data.get("model") not in MODELS:
        raise ValueError("unsupported reconstruction model")
    if directory.parent.name != data["model"] or directory.name != data.get("candidateId"):
        raise ValueError("candidate path does not match manifest")
    if not CANDIDATE.fullmatch(directory.name):
        raise ValueError("candidate id must match candidate_NNN")
    if data.get("claim") != "temporary-shape-estimate-not-production-mesh":
        raise ValueError("AI reconstruction must not claim production topology")
    status = data.get("status")
    if status not in {"planned", "running", "generated", "validated", "failed", "rejected"}:
        raise ValueError("invalid reconstruction status")
    provenance = data.get("provenance", {})
    for key in ("repository", "revision", "weightsSha256", "runner"):
        if status in {"running", "generated", "validated"} and not provenance.get(key):
            raise ValueError(f"running candidate requires provenance.{key}")
    outputs = data.get("outputs", [])
    if status in {"generated", "validated"} and not outputs:
        raise ValueError("generated candidate requires outputs")
    for item in outputs:
        path = (directory / item["uri"]).resolve()
        if directory.resolve() not in path.parents:
            raise ValueError("candidate output escapes directory")
        if verify_files:
            if not path.is_file() or path.stat().st_size != item.get("bytes"):
                raise ValueError(f"missing or resized output: {item['uri']}")
            if sha256(path) != item.get("sha256"):
                raise ValueError(f"output checksum mismatch: {item['uri']}")
    return {"valid": True, "model": data["model"], "candidateId": data["candidateId"], "status": status}


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("candidate manifest must be an object")
    return value
