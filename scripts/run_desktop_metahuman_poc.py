#!/usr/bin/env python3
"""Launch the UE 5.8 desktop MetaHuman POC only after its hard gates pass."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent
PREFLIGHT_PATH = Path(__file__).with_name("preflight_desktop_metahuman_poc.py")
SPEC = importlib.util.spec_from_file_location("desktop_metahuman_poc_preflight", PREFLIGHT_PATH)
PREFLIGHT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(PREFLIGHT)


def build_launch_command(workspace: Path, engine: Path) -> list[str]:
    editor = engine / "Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor"
    project = workspace / "unreal/GahyeonDesktopMetaHumanPOC/GahyeonDesktopMetaHumanPOC.uproject"
    return [
        str(editor), str(project),
        "-nosourcecontrol", "-nop4", "-nosound", "-NoSplash", "-log",
        "-ResX=1280", "-ResY=720", "-windowed",
        "-r.Streaming.PoolSize=384", "-r.TextureStreaming=1",
        "-r.Lumen.DiffuseIndirect.Allow=0", "-r.Lumen.Reflections.Allow=0",
        "-r.ShadowQuality=1", "-r.HairStrands.Strands=0",
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=ROOT)
    parser.add_argument("--engine", type=Path, default=Path("/Users/Shared/Epic Games/UE_5.8"))
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workspace = args.workspace.expanduser().resolve()
    engine = args.engine.expanduser().resolve()
    preflight_args = argparse.Namespace(workspace=workspace, engine=engine, output=None)
    report = PREFLIGHT.inspect_desktop_metahuman_poc(preflight_args)
    command = build_launch_command(workspace, engine)
    result = {
        "readyToLaunch": report["readyToOpenEditor"],
        "preflight": report,
        "command": command,
        "launched": False,
    }
    if args.dry_run or not report["readyToOpenEditor"]:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if args.dry_run else 2

    process = subprocess.Popen(command, cwd=workspace, start_new_session=True)
    result["launched"] = True
    result["pid"] = process.pid
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
