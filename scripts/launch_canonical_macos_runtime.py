#!/usr/bin/env python3
"""Launch only the explicitly promoted canonical Unreal macOS runtime."""

from __future__ import annotations

import json
import ctypes
import os
from pathlib import Path
import platform
import signal
import subprocess
import time


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config/canonical-character-runtime.json"
OVERLAY_SOURCE = ROOT / "native/macos/GahyeonUnrealOverlay/main.swift"
OVERLAY_BINARY = ROOT / ".build/macos-overlay/GahyeonUnrealOverlay"
SHARED_MEMORY_NAME = b"/gahyeon_rgba_v003"
IOSURFACE_MEMORY_NAME = b"/gahyeon_iosurface_v001"
OVERLAY_CONTROL_MEMORY_NAME = b"/gahyeon_overlay_control_v001"


def load_manifest() -> dict:
    value = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if value.get("schemaVersion") != 1 or value.get("runtime") != "unreal":
        raise RuntimeError("canonical runtime manifest must select Unreal")
    if "electron" not in value.get("retiredRuntimes", []):
        raise RuntimeError("canonical runtime manifest must keep Electron retired")
    return value


def build_command(value: dict) -> list[str]:
    if platform.system() != "Darwin":
        raise RuntimeError("this launcher is for macOS")
    macos = value["macos"]
    if value.get("status") != "ready" or not macos.get("runtimeMap"):
        blockers = "; ".join(value.get("blockers", [])) or "runtime is not promoted"
        raise RuntimeError(f"canonical Unreal service is not ready: {blockers}")
    editor = Path(macos["engineRoot"]) / "Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor"
    project = ROOT / macos["project"]
    missing = [str(path) for path in (editor, project) if not path.is_file()]
    if missing:
        raise RuntimeError(f"canonical Unreal prerequisites missing: {missing}")
    looking_glass_mode = os.environ.get("GAHYEON_LOOKING_GLASS_QUILT") == "1"
    runtime_map = macos["runtimeMap"]
    if looking_glass_mode:
        runtime_map = os.environ.get("GAHYEON_LOOKING_GLASS_RUNTIME_MAP", runtime_map)
    quality_commands = ",".join((
        "r.MotionBlurQuality 0",
        "r.DefaultFeature.MotionBlur 0",
        f"r.ScreenPercentage {125 if looking_glass_mode else 100}",
        "r.MaxAnisotropy 16",
        f"r.SkeletalMeshLODBias {0 if looking_glass_mode else -1}",
        "r.MipMapLODBias -1",
        f"r.TextureStreaming {1 if looking_glass_mode else 0}",
        f"r.Streaming.PoolSize {512 if looking_glass_mode else 0}",
        f"sg.AntiAliasingQuality {2 if looking_glass_mode else 4}",
        "r.AntiAliasingMethod 1",
        f"r.Tonemapper.Sharpen {0.8 if looking_glass_mode else 0.0}",
        "r.ExposureOffset 0.5",
        "r.PostProcessing.PropagateAlpha 1",
        f"sg.ShadowQuality {2 if looking_glass_mode else 4}",
        f"sg.TextureQuality {2 if looking_glass_mode else 4}",
        f"sg.EffectsQuality {2 if looking_glass_mode else 4}",
        f"sg.PostProcessQuality {2 if looking_glass_mode else 4}",
    ))
    command = [
        str(editor), str(project), runtime_map,
        "-game", "-windowed", "-ForceRes", "-ResX=1600", "-ResY=1258", "-NoSplash",
        "-nosourcecontrol", "-nop4",
        "-GahyeonAutoStartMicrophone", f"-ExecCmds={quality_commands}",
    ]
    if looking_glass_mode:
        command.append("-GahyeonLookingGlassQuilt")
    else:
        command.append("-GahyeonCPUAlphaFallback")
    return command


def build_overlay() -> Path:
    OVERLAY_BINARY.parent.mkdir(parents=True, exist_ok=True)
    if not OVERLAY_BINARY.is_file() or OVERLAY_BINARY.stat().st_mtime < OVERLAY_SOURCE.stat().st_mtime:
        subprocess.run(
            ["swiftc", "-swift-version", "5", str(OVERLAY_SOURCE), "-o", str(OVERLAY_BINARY)],
            cwd=ROOT,
            check=True,
        )
    return OVERLAY_BINARY


def frontmost_application_name() -> str:
    result = subprocess.run(
        ["osascript", "-e", 'tell application "System Events" to get name of first process whose frontmost is true'],
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip()


def reactivate_application(name: str) -> None:
    if not name or name == "UnrealEditor":
        return
    escaped = name.replace('"', '\\"')
    subprocess.run(["osascript", "-e", f'tell application "{escaped}" to activate'], check=False)


def unlink_stale_shared_memory() -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    libc.shm_unlink.argtypes = [ctypes.c_char_p]
    libc.shm_unlink(SHARED_MEMORY_NAME)
    libc.shm_unlink(IOSURFACE_MEMORY_NAME)
    libc.shm_unlink(OVERLAY_CONTROL_MEMORY_NAME)


def terminate_existing_runtime(command: list[str], overlay_binary: Path) -> None:
    """Remove only orphaned instances of this exact Unreal project and overlay."""
    result = subprocess.run(
        ["ps", "-axo", "pid=,command="], text=True, capture_output=True, check=True
    )
    editor, project = command[:2]
    targets: list[int] = []
    for line in result.stdout.splitlines():
        fields = line.strip().split(maxsplit=1)
        if len(fields) != 2:
            continue
        pid_text, process_command = fields
        if process_command == str(overlay_binary) or (
            process_command.startswith(editor + " ") and project in process_command
        ):
            pid = int(pid_text)
            if pid != os.getpid():
                targets.append(pid)
    for pid in targets:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    deadline = time.monotonic() + 3.0
    remaining = set(targets)
    while remaining and time.monotonic() < deadline:
        remaining = {pid for pid in remaining if _process_exists(pid)}
        if remaining:
            time.sleep(0.05)
    for pid in remaining:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def _process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def main() -> int:
    command = build_command(load_manifest())
    prior_application = frontmost_application_name()
    overlay_binary = build_overlay()
    terminate_existing_runtime(command, overlay_binary)
    unlink_stale_shared_memory()
    unreal = subprocess.Popen(command, cwd=ROOT)
    overlay = None if os.environ.get("GAHYEON_LOOKING_GLASS_NO_OVERLAY") == "1" else subprocess.Popen(
        [str(overlay_binary)], cwd=ROOT
    )
    try:
        time.sleep(5)
        reactivate_application(prior_application)
        while unreal.poll() is None and (overlay is None or overlay.poll() is None):
            time.sleep(0.25)
        if overlay is not None and overlay.poll() is not None and unreal.poll() is None:
            unreal.terminate()
        return unreal.wait()
    finally:
        if unreal.poll() is None:
            unreal.terminate()
        if overlay is not None and overlay.poll() is None:
            overlay.terminate()
        if overlay is not None:
            try:
                overlay.wait(timeout=3)
            except subprocess.TimeoutExpired:
                overlay.kill()


if __name__ == "__main__":
    raise SystemExit(main())
