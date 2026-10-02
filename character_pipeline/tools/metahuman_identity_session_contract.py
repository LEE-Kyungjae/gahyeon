#!/usr/bin/env python3
"""Pure-Python contract shared by the v002 Unreal importer and its tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    if not path.is_absolute() or not path.is_file() or path.is_symlink():
        raise ValueError(f"missing or unsafe absolute input: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def validate_import(session_path: Path) -> tuple[dict, Path]:
    session = load(session_path)
    if session.get("sessionId") != "gahyeon-metahuman-identity-v002":
        raise ValueError("wrong MetaHuman Identity session")
    if session.get("state") != "ready-to-launch" or session.get("blockedChecks"):
        raise ValueError("MetaHuman Identity session is not ready to launch")
    if session.get("qualityClaim") is not None:
        raise ValueError("session fabricates a quality claim")
    for key in ("handoff", "preflight", "source"):
        item = session.get(key, {})
        path = Path(item.get("path", ""))
        if not path.is_absolute() or not path.is_file() or path.is_symlink():
            raise ValueError(f"unsafe session lineage: {key}")
        if sha256(path) != item.get("sha256"):
            raise ValueError(f"session lineage checksum differs: {key}")
    preflight = load(Path(session["preflight"]["path"]))
    if preflight.get("readyToLaunchIdentitySolve") is not True:
        raise ValueError("preflight is no longer ready")
    required = {
        "engineInstalled", "engineVersionSupported", "editorPresent",
        "metaHumanCoreDataPresent", "allRequiredPluginsPresent",
        "identityInputVerifiedShape", "immutableHandoffVerified",
        "minimumMemory", "minimumRuntimeFreeDiskHeadroom",
    }
    checks = preflight.get("checks", {})
    if any(checks.get(key) is not True for key in required):
        raise ValueError("required preflight check is false")
    source = Path(session["source"]["path"])
    if source.suffix.lower() not in {".obj", ".fbx"}:
        raise ValueError("unsupported Identity input format")
    unreal = session.get("unreal", {})
    if unreal.get("replaceExisting") is not False:
        raise ValueError("session permits asset replacement")
    return session, source


def build_receipt(session_path: Path, session: dict, imported_asset: str) -> dict:
    if not imported_asset.startswith("/Game/"):
        raise ValueError("imported asset path is outside /Game")
    return {
        "schemaVersion": 1,
        "state": "shape-imported-awaiting-guided-identity",
        "session": {"path": str(session_path), "sha256": sha256(session_path)},
        "source": session["source"],
        "asset": {"path": imported_asset, "class": "StaticMesh"},
        "identityAsset": None,
        "identitySolved": False,
        "characterConformed": False,
        "automaticApproval": False,
        "qualityClaim": None,
        "nextRequiredStage": "components-from-mesh",
    }


def verify_receipt(session_path: Path, receipt_path: Path) -> dict:
    session = load(session_path)
    receipt = load(receipt_path)
    if receipt.get("state") != "shape-imported-awaiting-guided-identity":
        raise ValueError("receipt overclaims import state")
    if receipt.get("session") != {"path": str(session_path), "sha256": sha256(session_path)}:
        raise ValueError("receipt session lineage differs")
    if receipt.get("source") != session.get("source"):
        raise ValueError("receipt source lineage differs")
    if receipt.get("asset", {}).get("class") != "StaticMesh" or not receipt["asset"]["path"].startswith("/Game/"):
        raise ValueError("receipt asset differs")
    if any(receipt.get(key) is not False for key in ("identitySolved", "characterConformed", "automaticApproval")):
        raise ValueError("receipt overclaims MetaHuman progress")
    if receipt.get("qualityClaim") is not None or receipt.get("nextRequiredStage") != "components-from-mesh":
        raise ValueError("receipt bypasses guided Identity work")
    return {"valid": True, "state": receipt["state"], "qualityClaim": None}
