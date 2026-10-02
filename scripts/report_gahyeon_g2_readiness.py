#!/usr/bin/env python3
"""Report fail-closed readiness for the Fab-grade G2 character rebase."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REQUIRED_UNREAL_PLUGINS = {
    "ControlRig",
    "FullBodyIK",
    "HairStrands",
    "RigLogic",
    "ChaosCloth",
}
REQUIRED_G2_ARTIFACT_ROLES = {"high-poly-master", "animation-mesh"}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def enabled_plugins(project: dict[str, Any]) -> set[str]:
    return {
        item.get("Name")
        for item in project.get("Plugins", [])
        if isinstance(item, dict) and item.get("Enabled") is True
        and isinstance(item.get("Name"), str)
    }


def inspect(workspace: Path, project_path: Path) -> dict[str, Any]:
    g1_path = workspace / "g1-review.json"
    g2_path = workspace / "g2-review.json"
    g1 = load_json(g1_path) if g1_path.is_file() else {}
    g2 = load_json(g2_path) if g2_path.is_file() else {}
    project = load_json(project_path)

    plugins = enabled_plugins(project)
    evidence = g1.get("evidence", []) if isinstance(g1.get("evidence"), list) else []
    approvals = g1.get("approvals", []) if isinstance(g1.get("approvals"), list) else []
    g2_artifacts = g2.get("artifacts", []) if isinstance(g2.get("artifacts"), list) else []
    roles = {
        item.get("role") for item in g2_artifacts
        if isinstance(item, dict) and isinstance(item.get("role"), str)
    }

    checks = {
        "g1Approved": g1.get("status") == "approved",
        "g1EvidenceComplete": len(evidence) == 15,
        "g1ModelRegistered": isinstance(g1.get("modelArtifact"), dict),
        "g1HasApprovals": len(approvals) > 0,
        "g2ReviewStarted": bool(g2),
        "g2MasterArtifactsPresent": REQUIRED_G2_ARTIFACT_ROLES <= roles,
        "unrealProductionPluginsEnabled": REQUIRED_UNREAL_PLUGINS <= plugins,
    }
    missing_plugins = sorted(REQUIRED_UNREAL_PLUGINS - plugins)
    missing_roles = sorted(REQUIRED_G2_ARTIFACT_ROLES - roles)

    return {
        "schemaVersion": 1,
        "target": "fab-human-paid-product-minimum",
        "readyForFormalG2Candidate": all(checks.values()),
        "checks": checks,
        "g1": {
            "review": str(g1_path),
            "reviewSha256": sha256(g1_path) if g1_path.is_file() else None,
            "status": g1.get("status", "not-started"),
            "evidenceCount": len(evidence),
            "approvalCount": len(approvals),
        },
        "g2": {
            "review": str(g2_path),
            "status": g2.get("status", "not-started"),
            "artifactRoles": sorted(role for role in roles if role),
            "missingArtifactRoles": missing_roles,
        },
        "unreal": {
            "project": str(project_path),
            "engineAssociation": project.get("EngineAssociation"),
            "enabledPlugins": sorted(plugins),
            "missingProductionPlugins": missing_plugins,
        },
        "nextActions": [
            message for condition, message in (
                (not checks["g1EvidenceComplete"], "render and review all 15 sealed G1 views"),
                (not checks["g1ModelRegistered"], "register a visually accepted G1 model artifact"),
                (not checks["g1Approved"], "resolve likeness blockers and obtain independent G1 approvals"),
                (not checks["g2ReviewStarted"], "create G2 review only after an approved G1 predecessor"),
                (bool(missing_roles), "author high-poly face/body master and animation mesh"),
                (bool(missing_plugins), "enable and validate required Unreal production plugins"),
            ) if condition
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = inspect(args.workspace.resolve(), args.project.resolve())
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

