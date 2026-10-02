#!/usr/bin/env python3
"""Shared immutable iteration contract."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any


VERSION = re.compile(r"^v([0-9]{3,})$")
SCORE_KEYS = (
    "identitySimilarity", "faceGeometry", "bodyGeometry", "skin", "eyes",
    "hair", "materials", "rig", "facialDeformation", "bodyDeformation",
    "lightingRobustness", "closeUpQuality", "runtimePerformance", "overall",
)


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("iteration manifest must be an object")
    return value


def validate(data: dict[str, Any], directory: Path, *, verify_files: bool = True) -> dict[str, Any]:
    version = data.get("version")
    if not isinstance(version, str) or not VERSION.fullmatch(version):
        raise ValueError("version must match vNNN")
    if directory.name != version:
        raise ValueError("directory and manifest version differ")
    if data.get("schemaVersion") != 1 or data.get("characterId") != "gahyeon":
        raise ValueError("unsupported iteration identity/schema")
    hypothesis = data.get("hypothesis", {})
    for key in ("statement", "action", "expectedResult"):
        if not isinstance(hypothesis.get(key), str) or not hypothesis[key].strip():
            raise ValueError(f"hypothesis.{key} is required")
    state = data.get("state")
    if state not in {"planned", "running", "evaluated", "accepted", "rejected", "failed"}:
        raise ValueError("invalid iteration state")
    scores = data.get("evaluation", {}).get("scores", {})
    if set(scores) != set(SCORE_KEYS):
        raise ValueError("evaluation score keys are incomplete")
    for key, score in scores.items():
        if score is not None and (not isinstance(score, (int, float)) or not 0 <= score <= 100):
            raise ValueError(f"score out of range: {key}")
    if scores["overall"] is not None and any(scores[key] is None for key in SCORE_KEYS[:-1]):
        raise ValueError("overall score requires every component score")
    artifacts = data.get("artifacts", [])
    seen = set()
    for item in artifacts:
        uri = item.get("uri") if isinstance(item, dict) else None
        if not isinstance(uri, str) or not uri or uri in seen:
            raise ValueError("artifact URI is missing or duplicated")
        seen.add(uri)
        path = (directory / uri).resolve()
        if directory.resolve() not in path.parents:
            raise ValueError("artifact escapes iteration directory")
        if verify_files:
            if not path.is_file() or path.stat().st_size != item.get("bytes"):
                raise ValueError(f"artifact missing or resized: {uri}")
            if sha256(path) != item.get("sha256"):
                raise ValueError(f"artifact checksum mismatch: {uri}")
    decision = data.get("decision")
    if state in {"accepted", "rejected"}:
        if not isinstance(decision, dict) or decision.get("result") != state:
            raise ValueError("terminal iteration requires matching decision")
        if not isinstance(decision.get("rationale"), str) or not decision["rationale"].strip():
            raise ValueError("terminal decision rationale is required")
    return {"valid": True, "version": version, "state": state, "artifactCount": len(artifacts)}

