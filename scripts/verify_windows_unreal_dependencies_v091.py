#!/usr/bin/env python3
"""Fail-closed dependency check for the v091 native Windows runtime proof."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PROJECT_PLUGINS = {
    "AudioCapture",
    "ControlRig",
    "FullBodyIK",
    "EnhancedInput",
    "LiveLink",
    "LiveLinkControlRig",
    "AppleARKitFaceSupport",
}

ENGINE_PLUGIN_GROUPS = {
    "AnimationData": ("AnimationData",),
    "ControlRig": ("ControlRig",),
    "FullBodyIK": ("FullBodyIK",),
    "IKRig": ("IKRig",),
    "RigLogic": ("RigLogic",),
    "HairStrands": ("HairStrands",),
    "MetaHumanSDK": ("MetaHumanSDK",),
    "MetaHumanCharacter": ("MetaHumanCharacter",),
    "MetaHumanAnimator": ("MetaHuman", "MetaHumanAnimator"),
}


def plugin_index(engine: Path) -> dict[str, Path]:
    root = engine / "Engine" / "Plugins"
    if not root.is_dir():
        return {}
    return {path.stem: path for path in root.rglob("*.uplugin")}


def inspect(engine: Path, workspace: Path) -> dict[str, Any]:
    project = workspace / "unreal/GahyeonStage/GahyeonStage.uproject"
    try:
        descriptor = json.loads(project.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        descriptor = {}

    enabled = {
        item.get("Name")
        for item in descriptor.get("Plugins", [])
        if item.get("Enabled") is True
    }
    index = plugin_index(engine)
    resolved_plugins = {
        role: next((str(index[name]) for name in names if name in index), None)
        for role, names in ENGINE_PLUGIN_GROUPS.items()
    }
    markers = {
        "metaHumanHeadTemplate": engine
        / "Engine/Plugins/MetaHuman/MetaHumanSDK/Content/TemplateAssets/SM_MH_Head.uasset",
        "metaHumanCharacterContent": engine
        / "Engine/Plugins/MetaHuman/MetaHumanCharacter/Content",
        "visualBlueprint": workspace
        / "unreal/GahyeonStage/Content/Gahyeon/CharacterPipeline/v088/AssembledMedium/Skotukeda_WardrobeGroomQA_v088/BP_Skotukeda_WardrobeGroomQA_v088.uasset",
        "runtimeMap": workspace
        / "unreal/GahyeonStage/Content/Gahyeon/DesktopRuntime/v091/L_GahyeonDesktopRuntime_v091.umap",
        "fabMetaHuman": workspace
        / "unreal/GahyeonStage/Content/Fab/MetaHuman/Skotukeda.uasset",
    }
    checks = {
        "engineVersion58": engine.name == "UE_5.8",
        "runUatPresent": (engine / "Engine/Build/BatchFiles/RunUAT.bat").is_file(),
        "editorPresent": (engine / "Engine/Binaries/Win64/UnrealEditor.exe").is_file(),
        "projectDescriptorPresent": project.is_file(),
        "projectEngine58": descriptor.get("EngineAssociation") == "5.8",
        "projectPluginsEnabled": PROJECT_PLUGINS <= enabled,
        "enginePluginsPresent": all(resolved_plugins.values()),
        "metaHumanCoreDataPresent": all(
            path.exists()
            for name, path in markers.items()
            if name.startswith("metaHuman")
        ),
        "runtimeAssetsPresent": all(
            path.is_file()
            for name, path in markers.items()
            if not name.startswith("metaHuman")
        ),
    }
    missing_project_plugins = sorted(PROJECT_PLUGINS - enabled)
    missing_engine_plugins = sorted(
        role for role, path in resolved_plugins.items() if path is None
    )
    missing_markers = sorted(name for name, path in markers.items() if not path.exists())
    return {
        "schemaVersion": 1,
        "status": "ready" if all(checks.values()) else "blocked",
        "readyForWindowsPackage": all(checks.values()),
        "engine": str(engine),
        "workspace": str(workspace),
        "checks": checks,
        "missingProjectPlugins": missing_project_plugins,
        "missingEnginePlugins": missing_engine_plugins,
        "missingMarkers": missing_markers,
        "resolvedEnginePlugins": resolved_plugins,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = inspect(args.engine.resolve(), args.workspace.resolve())
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if report["readyForWindowsPackage"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
