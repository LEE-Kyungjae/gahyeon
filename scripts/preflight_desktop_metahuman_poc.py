#!/usr/bin/env python3
"""Fail-closed preflight for the low-memory desktop MetaHuman POC."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any


REQUIRED_PLUGINS = {
    "AnimationData", "ControlRig", "FullBodyIK", "IKRig", "RigLogic",
    "HairStrands", "MetaHumanSDK", "MetaHumanCharacter", "MetaHuman",
}
EDITOR_FREE_MEMORY_GIB = 10


def metahuman_optional_content_markers(engine: Path) -> dict[str, Path]:
    content = engine / "Engine/Plugins/MetaHuman/MetaHumanCharacter/Content/Optional"
    return {
        "textureSynthesis": content / "TextureSynthesis/TS-1.3-F_UE_res-1024_nchr-153",
        "skinMicrotiling": content / "BodyTextures/T_Skin_Microtiling_M.uasset",
        "templateAnimations": content / "Animation/TemplateAnimations/DT_MH_TemplateAnimations.uasset",
    }


def command_output(*command: str) -> str:
    try:
        return subprocess.check_output(command, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def available_memory_bytes() -> int:
    """Return a conservative macOS available-memory estimate."""
    total = int(command_output("sysctl", "-n", "hw.memsize") or 0)
    pressure = command_output("memory_pressure", "-Q")
    match = re.search(r"free percentage:\s*(\d+)%", pressure)
    return total * int(match.group(1)) // 100 if match and total else 0


def sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_project_plugins(project: dict[str, Any]) -> tuple[bool, list[str]]:
    enabled = {
        item.get("Name") for item in project.get("Plugins", [])
        if item.get("Enabled") is True
    }
    missing = sorted(REQUIRED_PLUGINS - enabled)
    return not missing, missing


def inspect_desktop_metahuman_poc(args: argparse.Namespace) -> dict[str, Any]:
    workspace = args.workspace.resolve()
    project_root = workspace / "unreal/GahyeonDesktopMetaHumanPOC"
    descriptor = project_root / "GahyeonDesktopMetaHumanPOC.uproject"
    asset = project_root / "Content/Fab/MetaHuman/Skotukeda.uasset"
    startup = project_root / "Content/Python/init_unreal.py"
    source_asset = workspace / "unreal/GahyeonStage/Content/Fab/MetaHuman/Skotukeda.uasset"
    engine = args.engine.expanduser().resolve()
    editor = engine / "Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor"

    try:
        project = json.loads(descriptor.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        project = {}
    plugins_valid, missing_plugins = validate_project_plugins(project)
    optional_markers = metahuman_optional_content_markers(engine)
    optional_checks = {name: path.exists() for name, path in optional_markers.items()}
    available = available_memory_bytes()
    threshold = EDITOR_FREE_MEMORY_GIB * 1024**3
    asset_hash = sha256(asset)
    source_hash = sha256(source_asset)
    same_inode = (
        asset.is_file() and source_asset.is_file()
        and asset.stat().st_ino == source_asset.stat().st_ino
        and asset.stat().st_dev == source_asset.stat().st_dev
    )
    checks = {
        "engine58Present": editor.is_file() and engine.name == "UE_5.8",
        "projectDescriptorValid": project.get("EngineAssociation") == "5.8",
        "requiredPluginsEnabled": plugins_valid,
        "startupAutomationPresent": startup.is_file(),
        "skotukedaAssetPresent": asset_hash is not None,
        "assetMatchesImportedSource": asset_hash is not None and asset_hash == source_hash,
        "assetUsesSpaceEfficientHardlink": same_inode,
        "editorFreeMemoryGate": available >= threshold,
    }
    static_checks = {key: value for key, value in checks.items() if key != "editorFreeMemoryGate"}
    return {
        "schemaVersion": 1,
        "readyToOpenEditor": all(checks.values()),
        "readyExceptForMemory": all(static_checks.values()) and not checks["editorFreeMemoryGate"],
        "readyForSurfaceQuality": all(checks.values()) and all(optional_checks.values()),
        "checks": checks,
        "surfaceQualityChecks": optional_checks,
        "memory": {
            "estimatedAvailableGiB": round(available / 1024**3, 2),
            "requiredAvailableGiB": EDITOR_FREE_MEMORY_GIB,
        },
        "project": str(descriptor),
        "asset": {"path": str(asset), "sha256": asset_hash, "hardlinked": same_inode},
        "missingPlugins": missing_plugins,
        "actions": [
            message for failed, message in (
                (not checks["engine58Present"], "install or select Unreal Engine 5.8"),
                (not checks["requiredPluginsEnabled"], "enable all required MetaHuman plugins"),
                (not checks["skotukedaAssetPresent"], "restore the imported Skotukeda asset"),
                (not checks["editorFreeMemoryGate"], "free at least 10 GiB before opening the auto-rigged MetaHuman editor"),
                (not all(optional_checks.values()), "install UE 5.8 MetaHuman Creator Core Data before surface-quality work"),
            ) if failed
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--engine", type=Path, default=Path("/Users/Shared/Epic Games/UE_5.8"))
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = inspect_desktop_metahuman_poc(args)
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if report["readyToOpenEditor"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
