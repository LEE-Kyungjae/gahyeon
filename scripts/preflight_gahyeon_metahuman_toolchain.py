#!/usr/bin/env python3
"""Fail-closed preflight for the real Gahyeon MetaHuman toolchain."""

from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
from typing import Any


PLUGIN_CANDIDATES = {
    # UE 5.8 moved the in-editor Creator workflow into MetaHumanCharacter and
    # ships Animator as MetaHuman.uplugin. Keep the legacy names so the same
    # preflight remains valid for supported 5.6/5.7 installations.
    "MetaHumanCreator": ("MetaHumanCreator", "MetaHumanCharacter"),
    "MetaHumanAnimator": ("MetaHumanAnimator", "MetaHuman"),
    "MetaHumanAnimatorDepthProcessing": (
        "MetaHumanAnimatorDepthProcessing", "MetaHumanDepthProcessing",
        "MetaHumanCalibrationProcessing",
    ),
    "RigLogic": ("RigLogic",),
    "HairStrands": ("HairStrands",),
}


def command_output(*command: str) -> str:
    try:
        return subprocess.check_output(command, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def engine_candidates(explicit: Path | None) -> list[Path]:
    values = []
    if explicit:
        values.append(explicit.expanduser().resolve())
    for root in (Path("/Users/Shared/Epic Games"), Path("/Applications")):
        if root.is_dir():
            values.extend(path for path in root.glob("UE_5.*") if path.is_dir())
    unique = {str(path): path for path in values}
    return sorted(unique.values(), key=lambda path: path.name, reverse=True)


def locate_plugin(engine: Path, names: tuple[str, ...], plugin_index: dict[str, str] | None = None) -> str | None:
    if plugin_index is not None:
        return next((plugin_index.get(name) for name in names if plugin_index.get(name)), None)
    roots = (engine / "Engine" / "Plugins", engine / "Plugins")
    for root in roots:
        for name in names:
            if not root.is_dir():
                continue
            matches = tuple(root.rglob(f"{name}.uplugin"))
            if matches:
                return str(matches[0])
    return None


def index_plugins(engine: Path) -> dict[str, str]:
    """Index installed plugin descriptors once instead of rescanning UE per role."""
    result: dict[str, str] = {}
    for root in (engine / "Engine" / "Plugins", engine / "Plugins"):
        if not root.is_dir():
            continue
        for descriptor in root.rglob("*.uplugin"):
            result.setdefault(descriptor.stem, str(descriptor))
    return result


def metahuman_core_data_markers(engine: Path) -> list[str]:
    """Return real cooked MetaHuman assets without traversing UE source/build trees."""
    required = (
        engine / "Engine/Plugins/MetaHuman/MetaHumanAnimator/Content/MeshFitting/Mesh2MetaHuman.uasset",
        engine / "Engine/Plugins/MetaHuman/MetaHumanSDK/Content/TemplateAssets/SM_MH_Head.uasset",
        engine / "Engine/Plugins/MetaHuman/MetaHumanCharacter/Content",
    )
    return [str(path) for path in required if path.exists()]


def engine_version(engine: Path | None) -> tuple[int, int] | None:
    if engine is None:
        return None
    name = engine.name.removeprefix("UE_")
    parts = name.split(".")
    try:
        return int(parts[0]), int(parts[1])
    except (IndexError, ValueError):
        return None


def verify_handoff(workspace: Path, handoff: Path) -> tuple[bool, str]:
    verifier = workspace / "character_pipeline" / "tools" / "verify_metahuman_handoff.py"
    if not verifier.is_file() or not handoff.is_file():
        return False, "handoff or verifier missing"
    result = subprocess.run(
        [sys.executable, str(verifier), str(handoff)],
        text=True,
        capture_output=True,
        check=False,
    )
    detail = (result.stdout if result.returncode == 0 else result.stderr).strip()
    return result.returncode == 0, detail


def inspect(args: argparse.Namespace) -> dict[str, Any]:
    workspace = args.workspace.expanduser().resolve()
    engines = engine_candidates(args.engine)
    engine = engines[0] if engines else None
    version = engine_version(engine)
    launcher = Path("/Applications/Epic Games Launcher.app")
    input_manifest = args.identity_input / "manifest.json"
    input_data = (
        json.loads(input_manifest.read_text(encoding="utf-8"))
        if input_manifest.is_file() else {}
    )
    memory_bytes = int(command_output("sysctl", "-n", "hw.memsize") or 0)
    free_bytes = shutil.disk_usage(args.workspace).free
    handoff_verified, handoff_detail = verify_handoff(workspace, args.handoff.expanduser().resolve())
    chip = command_output("sysctl", "-n", "machdep.cpu.brand_string")
    if platform.machine() == "arm64":
        chip = command_output("system_profiler", "SPHardwareDataType") or chip

    plugin_index = index_plugins(engine) if engine else {}
    plugins = {
        role: locate_plugin(engine, names, plugin_index) if engine else None
        for role, names in PLUGIN_CANDIDATES.items()
    }
    editor_candidates = (
        [engine / "Engine" / "Binaries" / "Mac" / "UnrealEditor.app"]
        if engine else []
    )
    editor = next((path for path in editor_candidates if path.exists()), None)
    core_data_markers = metahuman_core_data_markers(engine) if engine else []

    checks = {
        "launcherInstalled": launcher.is_dir(),
        "engineInstalled": engine is not None,
        "engineVersionSupported": version is not None and version >= (5, 6),
        "editorPresent": editor is not None,
        "metaHumanCoreDataPresent": len(core_data_markers) == 3,
        "allRequiredPluginsPresent": all(plugins.values()),
        "identityInputVerifiedShape": (
            input_data.get("claim") == "neutral-static-mesh-input-not-metahuman-not-dna"
            and input_data.get("scope") == "head-neck-and-eyes-only"
            and input_data.get("mesh", {}).get("vertices", 0) >= 4_000
            and input_data.get("mesh", {}).get("polygons", 0) >= 4_000
        ),
        "immutableHandoffVerified": handoff_verified,
        "minimumMemory": memory_bytes >= 16 * 1024**3,
        "recommendedMetaHumanMemory": memory_bytes >= 32 * 1024**3,
        "minimumFreeDiskHeadroom": free_bytes >= 80 * 1024**3,
        "minimumRuntimeFreeDiskHeadroom": free_bytes >= 20 * 1024**3,
    }
    return {
        "schemaVersion": 1,
        "readyToLaunchIdentitySolve": all((
            checks["launcherInstalled"], checks["engineInstalled"],
            checks["engineVersionSupported"], checks["editorPresent"], checks["metaHumanCoreDataPresent"],
            checks["allRequiredPluginsPresent"], checks["identityInputVerifiedShape"],
            checks["immutableHandoffVerified"],
            checks["minimumMemory"], checks["minimumRuntimeFreeDiskHeadroom"],
        )),
        "checks": checks,
        "hardware": {
            "architecture": platform.machine(),
            "memoryGiB": round(memory_bytes / 1024**3, 2),
            "freeDiskGiB": round(free_bytes / 1024**3, 2),
            "chipEvidence": chip.splitlines()[0] if chip else "unknown",
        },
        "launcher": str(launcher) if launcher.is_dir() else None,
        "engine": str(engine) if engine else None,
        "engineVersion": ".".join(map(str, version)) if version else None,
        "editor": str(editor) if editor else None,
        "plugins": plugins,
        "metaHumanCoreDataMarkers": core_data_markers[:10],
        "identityInput": str(args.identity_input),
        "handoff": {
            "path": str(args.handoff),
            "verified": handoff_verified,
            "verification": handoff_detail,
        },
        "actions": [
            text for condition, text in (
                (not checks["engineInstalled"], "install Unreal Engine 5.6+ in Epic Games Launcher"),
                (checks["engineInstalled"] and not checks["engineVersionSupported"], "install or select Unreal Engine 5.6+"),
                (not checks["metaHumanCoreDataPresent"], "select MetaHuman Creator Core Data in Engine Options"),
                (not checks["allRequiredPluginsPresent"], "install MetaHuman Animator Depth Processing and required engine plugins"),
                (not checks["minimumFreeDiskHeadroom"], "provide at least 80 GiB free disk headroom before engine/Core Data installation"),
                (not checks["minimumRuntimeFreeDiskHeadroom"], "provide at least 20 GiB free disk headroom before an Identity solve"),
                (not checks["recommendedMetaHumanMemory"], "expect reduced throughput: 32 GiB RAM is recommended for MetaHuman Creator"),
                (not checks["immutableHandoffVerified"], "repair and verify the immutable v002 MetaHuman handoff before solving"),
            ) if condition
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--engine", type=Path)
    parser.add_argument(
        "--identity-input", type=Path,
        default=Path("artifacts/gahyeon-ch/metahuman-identity-input-v79-v4"),
    )
    parser.add_argument(
        "--handoff", type=Path,
        default=Path("character_pipeline/metahuman/identity/v002/handoff.json"),
    )
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = inspect(args)
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
