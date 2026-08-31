#!/usr/bin/env python3
"""One-stop canonical Unreal + Looking Glass Bridge launcher for macOS."""

from __future__ import annotations

import os
from pathlib import Path
import signal
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "native/macos/GahyeonLookingGlassBridge"
BUILD = ROOT / ".build/macos-looking-glass"
ENCODER = BUILD / "GahyeonLookingGlassFrameEncoder"
BRIDGE_APP = Path("/Applications/Looking Glass Bridge 2.6.3.app/Contents")


def build_encoder() -> None:
    BUILD.mkdir(parents=True, exist_ok=True)
    source = NATIVE / "frame_encoder.mm"
    if ENCODER.is_file() and ENCODER.stat().st_mtime >= source.stat().st_mtime:
        return
    subprocess.run([
        "clang++", "-std=c++17", "-Werror", "-Wall", "-Wextra", "-fobjc-arc",
        "-I", str(BRIDGE_APP / "runtime"), str(source),
        "-framework", "Foundation", "-framework", "AppKit",
        "-framework", "CoreGraphics", "-framework", "Metal",
        str(BRIDGE_APP / "MacOS/libbridge_inproc.dylib"),
        "-Wl,-rpath," + str(BRIDGE_APP / "MacOS"), "-o", str(ENCODER),
    ], cwd=ROOT, check=True)


def terminate(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def main() -> int:
    if sys.platform != "darwin":
        raise RuntimeError("Looking Glass one-stop runtime supports macOS only")
    subprocess.run([sys.executable, str(ROOT / "scripts/setup_looking_glass_macos.py"),
                    "--no-open-download"], cwd=ROOT, check=True)
    build_encoder()

    runtime_environment = os.environ.copy()
    runtime_environment["GAHYEON_LOOKING_GLASS_QUILT"] = "1"
    runtime_environment["GAHYEON_LOOKING_GLASS_NO_OVERLAY"] = "1"
    runtime = subprocess.Popen(
        [sys.executable, str(ROOT / "scripts/launch_canonical_macos_runtime.py")],
        cwd=ROOT,
        env=runtime_environment,
    )
    # The canonical launcher removes stale shared-memory segments before Unreal starts.
    # Do not let the encoder attach to the previous segment during that short window.
    time.sleep(2.0)
    stream = subprocess.Popen([str(ENCODER)], cwd=ROOT)
    stopping = False

    def stop(_signum=None, _frame=None):
        nonlocal stopping
        if stopping:
            return
        stopping = True
        terminate(stream)
        terminate(runtime)

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    try:
        while runtime.poll() is None and stream.poll() is None:
            time.sleep(0.25)
        return runtime.returncode if runtime.poll() is not None else stream.returncode
    finally:
        stop()


if __name__ == "__main__":
    raise SystemExit(main())
