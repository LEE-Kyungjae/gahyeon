#!/usr/bin/env python3
"""One-stop canonical Unreal + Looking Glass Bridge launcher for macOS."""

from __future__ import annotations

import ctypes
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "native/macos/GahyeonLookingGlassBridge"
BUILD = ROOT / ".build/macos-looking-glass"
ENCODER = BUILD / "GahyeonLookingGlassFrameEncoder"
BRIDGE_APP = Path("/Applications/Looking Glass Bridge 2.6.3.app/Contents")
BRIDGE_LIBRARY = BRIDGE_APP / "MacOS/libbridge_inproc.dylib"


def read_display_profile() -> tuple[float, int]:
    bridge = ctypes.CDLL(str(BRIDGE_LIBRARY))
    bridge.initialize_bridge.argtypes = [ctypes.c_char_p]
    bridge.initialize_bridge.restype = ctypes.c_bool
    bridge.get_displays.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_ulong)]
    bridge.get_displays.restype = ctypes.c_bool
    bridge.get_viewcone_for_display.argtypes = [ctypes.c_ulong, ctypes.POINTER(ctypes.c_float)]
    bridge.get_viewcone_for_display.restype = ctypes.c_bool
    bridge.get_default_quilt_settings_for_display.argtypes = [
        ctypes.c_ulong, ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int),
    ]
    bridge.get_default_quilt_settings_for_display.restype = ctypes.c_bool
    bridge.uninitialize_bridge.restype = ctypes.c_bool
    if not bridge.initialize_bridge(b"Gahyeon Looking Glass Calibration"):
        raise RuntimeError("Looking Glass Bridge calibration initialization failed")
    try:
        count = ctypes.c_int()
        if not bridge.get_displays(ctypes.byref(count), None) or count.value < 1:
            raise RuntimeError("no calibrated Looking Glass display found")
        display_ids = (ctypes.c_ulong * count.value)()
        if not bridge.get_displays(ctypes.byref(count), display_ids):
            raise RuntimeError("Looking Glass display enumeration failed")
        viewcone, aspect = ctypes.c_float(), ctypes.c_float()
        quilt_width, quilt_height = ctypes.c_int(), ctypes.c_int()
        columns, rows = ctypes.c_int(), ctypes.c_int()
        display_id = display_ids[0]
        if not bridge.get_viewcone_for_display(display_id, ctypes.byref(viewcone)):
            raise RuntimeError("Looking Glass view cone calibration unavailable")
        if not bridge.get_default_quilt_settings_for_display(
            display_id, ctypes.byref(aspect), ctypes.byref(quilt_width),
            ctypes.byref(quilt_height), ctypes.byref(columns), ctypes.byref(rows)
        ):
            raise RuntimeError("Looking Glass quilt calibration unavailable")
        view_count = columns.value * rows.value
        if not 1.0 <= viewcone.value <= 180.0 or not 2 <= view_count <= 256:
            raise RuntimeError("Looking Glass calibration values are invalid")
        return viewcone.value, view_count
    finally:
        bridge.uninitialize_bridge()


def build_encoder() -> None:
    BUILD.mkdir(parents=True, exist_ok=True)
    source = NATIVE / "frame_encoder.mm"
    dependencies = (source, NATIVE / "quilt_frame_cache.h")
    if ENCODER.is_file() and ENCODER.stat().st_mtime >= max(p.stat().st_mtime for p in dependencies):
        return
    subprocess.run([
        "clang++", "-std=c++17", "-Werror", "-Wall", "-Wextra", "-fobjc-arc",
        "-DGL_SILENCE_DEPRECATION", "-Wno-deprecated-declarations",
        "-I", str(BRIDGE_APP / "runtime"), str(source),
        "-framework", "Foundation", "-framework", "AppKit",
        "-framework", "CoreGraphics", "-framework", "IOSurface", "-framework", "Metal",
        "-framework", "OpenGL", "-lcompression",
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
    viewcone, view_count = read_display_profile()

    runtime_environment = os.environ.copy()
    runtime_environment["GAHYEON_LOOKING_GLASS_QUILT"] = "1"
    runtime_environment["GAHYEON_LOOKING_GLASS_NO_OVERLAY"] = "1"
    runtime_environment["GAHYEON_LOOKING_GLASS_VIEW_CONE"] = f"{viewcone:.6f}"
    runtime_environment["GAHYEON_LOOKING_GLASS_VIEW_COUNT"] = str(view_count)
    runtime_environment["GAHYEON_LOOKING_GLASS_RUNTIME_MAP"] = (
        "/Game/Gahyeon/Character2/Diana/v450/Runtime/L_DianaLookingGlassContactFloor_v450"
    )
    runtime_environment["GAHYEON_LOOKING_GLASS_ANIMATED_QA"] = "1"
    ready_directory = tempfile.TemporaryDirectory(prefix="gahyeon-lg-ready-")
    ready_file = Path(ready_directory.name) / "runtime.ready"
    runtime_environment["GAHYEON_RUNTIME_READY_FILE"] = str(ready_file)
    runtime = subprocess.Popen(
        [sys.executable, str(ROOT / "scripts/launch_canonical_macos_runtime.py")],
        cwd=ROOT,
        env=runtime_environment,
    )
    # Compilation/startup may exceed a fixed delay: wait for stale-memory cleanup.
    try:
        deadline = time.monotonic() + 120.0
        while not ready_file.is_file():
            if runtime.poll() is not None:
                raise RuntimeError("canonical runtime exited before consumer readiness")
            if time.monotonic() >= deadline:
                raise RuntimeError("canonical runtime consumer readiness timed out")
            time.sleep(0.05)
        time.sleep(2.0)
    except BaseException:
        terminate(runtime)
        raise
    finally:
        ready_directory.cleanup()
    stream_environment = os.environ.copy()
    stream_environment["GAHYEON_LOOKING_GLASS_ANIMATED_QA"] = "1"
    stream = subprocess.Popen([str(ENCODER)], cwd=ROOT, env=stream_environment)
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
