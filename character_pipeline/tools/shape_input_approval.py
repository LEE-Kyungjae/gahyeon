#!/usr/bin/env python3
"""Validate human, scope-bound approval of reconstruction RGBA inputs."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib, json
from pathlib import Path
from typing import Any


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_time(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None: raise ValueError("approval time must include timezone")
    return result.astimezone(timezone.utc)


def validate_shape_input_approval(config: dict[str, Any], approval: dict[str, Any],
                                  now: datetime | None = None, verify_files: bool = True) -> dict[str, Any]:
    if config.get("schemaVersion") != 1 or approval.get("schemaVersion") != 1:
        raise ValueError("unsupported shape approval schema")
    index=str(approval.get("canonicalIndex")); scope=approval.get("scope")
    if config["canonicalScope"].get(index)!=scope or scope not in config["allowedScopes"]:
        raise ValueError("approval scope exceeds canonical policy")
    if set(approval.get("exclusions",[])) != set(config["requiredExclusions"][scope]):
        raise ValueError("approval exclusions are incomplete")
    if approval.get("purpose") != config["allowedPurpose"] or approval.get("productionMeshAllowed") is not False:
        raise ValueError("approval purpose overclaims use")
    if approval.get("approved") is not True or approval.get("automatic") is not False:
        raise ValueError("shape input requires explicit human approval")
    reviewer=approval.get("reviewer",{});
    if not reviewer.get("name") or reviewer.get("role") not in {"character-owner","character-art-director"}:
        raise ValueError("approval requires authorized named reviewer")
    approved_at=parse_time(approval.get("approvedAt","")); expires_at=parse_time(approval.get("expiresAt","")); now=(now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    maximum_expiry = approved_at + timedelta(days=config["approvalValidityDays"])
    if approved_at > now or expires_at <= approved_at or expires_at > maximum_expiry or now > expires_at:
        raise ValueError("approval is future-dated or expired")
    derivative=approval.get("derivative",{}); path=Path(derivative.get("path",""))
    if not path.is_absolute() or path.is_symlink() or (verify_files and (not path.is_file() or digest(path)!=derivative.get("sha256"))):
        raise ValueError("approved derivative missing or checksum differs")
    matte_manifest=Path(approval.get("matteManifest",{}).get("path",""))
    if not matte_manifest.is_absolute() or matte_manifest.is_symlink() or (verify_files and (not matte_manifest.is_file() or digest(matte_manifest)!=approval["matteManifest"].get("sha256"))):
        raise ValueError("matte manifest missing or checksum differs")
    if verify_files:
        matte=json.loads(matte_manifest.read_text())
        if matte.get("canonicalIndex") != approval["canonicalIndex"] or matte.get("derivative",{}).get("sha256") != derivative["sha256"]:
            raise ValueError("approval and matte lineage differ")
    return {"valid":True,"canonicalIndex":approval["canonicalIndex"],"scope":scope,
            "reviewer":reviewer["name"],"expiresAt":expires_at.isoformat(),"productionMeshAllowed":False}


def validate_approval_request(config: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    index=str(request.get("canonicalIndex")); scope=request.get("scope")
    if config["canonicalScope"].get(index)!=scope or set(request.get("exclusions",[]))!=set(config["requiredExclusions"][scope]):
        raise ValueError("approval request scope or exclusions differ")
    if request.get("approved") is not False or request.get("automatic") is not False or request.get("reviewer") is not None:
        raise ValueError("approval request must remain unsigned")
    if request.get("purpose")!=config["allowedPurpose"] or request.get("productionMeshAllowed") is not False:
        raise ValueError("approval request purpose overclaims use")
    for key in ("derivative","matteManifest"):
        path=Path(request.get(key,{}).get("path",""))
        if not path.is_absolute() or not path.is_file() or path.is_symlink() or digest(path)!=request[key].get("sha256"):
            raise ValueError(f"approval request {key} checksum differs")
    matte=json.loads(Path(request["matteManifest"]["path"]).read_text())
    if matte.get("canonicalIndex")!=request["canonicalIndex"] or matte.get("derivative",{}).get("sha256")!=request["derivative"]["sha256"]:
        raise ValueError("approval request lineage differs")
    return {"valid":True,"canonicalIndex":request["canonicalIndex"],"scope":scope,"approved":False}
