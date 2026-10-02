#!/usr/bin/env python3
"""Launch the configured UE game window; this is not a packaged-app claim."""

from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "config/desktop-looking-glass-runtime-poc-v091.json"
PLATFORM_NAMES = {"Darwin": "macos", "Windows": "windows"}


def load_config(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schemaVersion") != 1 or value.get("iteration") != "v091":
        raise ValueError("unsupported runtime POC config")
    return value


def host_platform() -> str:
    try:
        return PLATFORM_NAMES[platform.system()]
    except KeyError as error:
        raise ValueError(f"unsupported desktop platform: {platform.system()}") from error


def default_engine(config: dict, target_platform: str) -> Path:
    return Path(config["platforms"][target_platform]["engineDefault"])


def build_command(root: Path, engine: Path, config: dict, log_path: Path,
                  target_platform: str) -> list[str]:
    desktop = config["desktop"]
    editor = engine / config["platforms"][target_platform]["editorRelative"]
    project = root / "unreal/GahyeonStage/GahyeonStage.uproject"
    return [
        str(editor), str(project), config["map"], "-game", "-windowed",
        f"-ResX={desktop['width']}", f"-ResY={desktop['height']}",
        "-WinX=80", "-WinY=80", "-nosourcecontrol", "-nop4", "-nosound",
        "-NoSplash", "-log", "-stdout", f"-abslog={log_path}",
        "-r.Streaming.PoolSize=512", "-r.TextureStreaming=1",
        "-r.Lumen.DiffuseIndirect.Allow=0", "-r.Lumen.Reflections.Allow=0",
        "-r.ShadowQuality=1", "-r.HairStrands.Strands=0",
    ]


def missing_prerequisites(command: list[str]) -> list[str]:
    return [path for path in command[:2] if not Path(path).is_file()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--platform", choices=("macos", "windows"), default=None)
    parser.add_argument("--engine", type=Path)
    parser.add_argument("--log", type=Path, default=Path("/tmp/gahyeon-desktop-runtime-v091.log"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--detach", action="store_true", help="Return after spawning instead of supervising UE")
    args = parser.parse_args()
    config = load_config(args.config.resolve())
    target_platform = args.platform or host_platform()
    engine = (args.engine or default_engine(config, target_platform)).resolve()
    command = build_command(ROOT, engine, config, args.log.resolve(), target_platform)
    missing = missing_prerequisites(command)
    result = {
        "mode": "unreal-game-window",
        "platform": target_platform,
        "packagedApp": False,
        "characterBlueprintContract": config["characterBlueprint"],
        "map": config["map"],
        "command": command,
        "missing": sorted(set(missing)),
        "launched": False,
    }
    if args.dry_run or missing:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if args.dry_run and not missing else 2
    process = subprocess.Popen(command, cwd=ROOT, start_new_session=args.detach)
    result.update(launched=True, pid=process.pid, supervised=not args.detach)
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    return 0 if args.detach else process.wait()


if __name__ == "__main__":
    raise SystemExit(main())
