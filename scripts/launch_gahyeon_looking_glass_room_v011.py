#!/usr/bin/env python3
"""Run the canonical Gahyeon idle preview on a calibrated Looking Glass Go."""
from __future__ import annotations
import argparse
import hashlib
import ctypes as C
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import launch_looking_glass_macos_runtime as legacy
import launch_canonical_macos_runtime as canonical

ROOT = Path(__file__).resolve().parents[1]
BINARY = legacy.BUILD / 'GahyeonLookingGlassPresenterV005'

def baseline_environment(profile: dict, manifest: dict, smooth: bool) -> dict:
    m = manifest['macos']
    if manifest.get('status') != 'ready' or m.get('characterModelId') != 'gahyeon':
        raise RuntimeError('Canonical character must be ready Gahyeon')
    animation = json.loads((ROOT / m['animationProfile']).read_text())
    seconds = next(a['seconds'] for a in animation['animations'] if a['role'] == 'idle')
    if not 0 < seconds < 3600:
        raise RuntimeError('Invalid idle duration')
    env = {k:v for k,v in os.environ.items() if not k.startswith('GAHYEON_LOOKING_GLASS_')}
    values = dict(QUILT='1', NO_OVERLAY='1', VIEW_CONE=str(profile['viewCone']), VIEW_COUNT=str(profile['viewCount']), DISPLAY_ID=str(profile['displayId']), RUNTIME_MAP=m['runtimeMap'], ANIMATED_QA='1', GL_UPLOAD='1', RENDER_PROFILE='tile-v001', STABLE_CAPTURE='1', CLIP_SECONDS=str(seconds))
    if smooth:
        values['SMOOTH_QA'] = '1'
    env.update({'GAHYEON_LOOKING_GLASS_' + k:v for k,v in values.items()})
    return env

def display_profile(serial: str) -> dict:
    b = C.CDLL(str(legacy.BRIDGE_LIBRARY))
    b.initialize_bridge.argtypes = [C.c_char_p]
    b.initialize_bridge.restype = C.c_bool
    b.get_displays.argtypes = [C.POINTER(C.c_int), C.POINTER(C.c_ulong)]
    b.get_displays.restype = C.c_bool
    b.get_device_serial_for_display.argtypes = [C.c_ulong, C.POINTER(C.c_int), C.c_wchar_p]
    b.get_device_serial_for_display.restype = C.c_bool
    b.get_viewcone_for_display.argtypes = [C.c_ulong, C.POINTER(C.c_float)]
    b.get_viewcone_for_display.restype = C.c_bool
    b.get_default_quilt_settings_for_display.argtypes = [C.c_ulong, C.POINTER(C.c_float)] + [C.POINTER(C.c_int)] * 4
    b.get_default_quilt_settings_for_display.restype = C.c_bool
    if not b.initialize_bridge(b'Gahyeon Serial Selection'):
        raise RuntimeError('Bridge initialization failed')
    try:
        n = C.c_int()
        if not b.get_displays(C.byref(n), None) or n.value < 1:
            raise RuntimeError('No calibrated display')
        ids = (C.c_ulong * n.value)()
        if not b.get_displays(C.byref(n), ids):
            raise RuntimeError('Display enumeration failed')
        for display_id in ids:
            length = C.c_int()
            b.get_device_serial_for_display(display_id, C.byref(length), None)
            buf = C.create_unicode_buffer(length.value + 1)
            if not b.get_device_serial_for_display(display_id, C.byref(length), buf) or buf.value != serial:
                continue
            aspect, cone = C.c_float(), C.c_float()
            width, height, cols, rows = (C.c_int() for _ in range(4))
            if not b.get_default_quilt_settings_for_display(display_id, C.byref(aspect), C.byref(width), C.byref(height), C.byref(cols), C.byref(rows)):
                raise RuntimeError('Quilt calibration missing')
            if not b.get_viewcone_for_display(display_id, C.byref(cone)):
                raise RuntimeError('View cone missing')
            if (width.value, height.value, cols.value, rows.value, aspect.value) != (4092, 4092, 11, 6, .5625):
                raise RuntimeError('Presenter requires Looking Glass Go 4092 / 11 x 6 calibration')
            if not 1 <= cone.value <= 180:
                raise RuntimeError('Invalid view cone')
            return dict(serial=serial, displayId=display_id, viewCone=cone.value, viewCount=cols.value*rows.value, aspect=aspect.value)
        raise RuntimeError(f'Connected display not found: {serial}')
    finally:
        b.uninitialize_bridge()

def build() -> None:
    legacy.BUILD.mkdir(parents=True, exist_ok=True)
    source = legacy.NATIVE / 'gahyeon_presenter_v005.mm'
    dependencies = [source, legacy.NATIVE / 'quilt_disk_cache.h']
    if BINARY.exists() and BINARY.stat().st_mtime >= max(p.stat().st_mtime for p in dependencies):
        return
    command = ['clang++', '-O2', '-std=c++17', '-Werror', '-Wall', '-Wextra', '-fobjc-arc', '-DGL_SILENCE_DEPRECATION', '-Wno-deprecated-declarations', '-I', str(legacy.BRIDGE_APP / 'runtime'), str(source)]
    for framework in ('Foundation', 'AppKit', 'CoreGraphics', 'IOSurface', 'Metal', 'OpenGL'):
        command += ['-framework', framework]
    command += ['-lcompression', str(legacy.BRIDGE_LIBRARY), '-Wl,-rpath,' + str(legacy.BRIDGE_APP / 'MacOS'), '-o', str(BINARY)]
    subprocess.run(command, cwd=ROOT, check=True)

def environment(profile: dict, manifest: dict, smooth: bool, room_config: str = 'looking-glass-room-v011.json') -> dict:
    env = baseline_environment(profile, manifest, True)
    if Path(room_config).name != room_config:
        raise ValueError('Room config must be a filename inside config/')
    scene = json.loads((ROOT / 'config' / room_config).read_text())
    if not scene['character'].split('.')[-1] == 'Gahyeon_Land_Idle_v001':
        raise RuntimeError('Room character identity mismatch')
    depth = float(scene.get('captureDepthScale', 0.45))
    if not math.isfinite(depth) or not 0.01 <= depth <= 1.0:
        raise ValueError('Capture depth scale must be finite and between 0.01 and 1.0')
    env['GAHYEON_LOOKING_GLASS_DEPTH_SCALE'] = str(depth)
    sample = min(float(scene['sampleSeconds']), float(env['GAHYEON_LOOKING_GLASS_CLIP_SECONDS']))
    if not 0 < sample <= 60 or scene['cachedFrames'] != 120:
        raise RuntimeError('Unsupported room sample settings')
    env['GAHYEON_LOOKING_GLASS_SAMPLE_SECONDS'] = str(sample)
    env['GAHYEON_LOOKING_GLASS_CLIP_SECONDS'] = str(sample)
    env['GAHYEON_LOOKING_GLASS_RUNTIME_MAP'] = scene['map']
    mapfile = ROOT / 'unreal/GahyeonDesktopMetaHumanPOC/Content' / (scene['map'].removeprefix('/Game/') + '.umap')
    signature_bytes = mapfile.read_bytes() + str(sample).encode() + b'room-v005-unmixed-248x454-lz4'
    # Preserve existing 0.45 caches; other baselines must never reuse their quilts.
    if depth != 0.45:
        signature_bytes += (';capture-depth=' + repr(depth)).encode()
    memory_mib = scene.get('compressedCacheMiB', 0)
    if type(memory_mib) is not int or not 0 <= memory_mib <= 1792:
        raise ValueError('Compressed cache memory cap must be an integer from 0 to 1792 MiB')
    env['GAHYEON_LOOKING_GLASS_COMPRESSED_CACHE_MIB'] = str(memory_mib)
    render_profile = scene.get('renderProfile', 'tile-v001')
    if render_profile not in ('tile-v001', 'portrait-v001'):
        raise ValueError('Unsupported room render profile')
    env['GAHYEON_LOOKING_GLASS_RENDER_PROFILE'] = render_profile
    if render_profile != 'tile-v001':
        signature_bytes += (';render-profile=' + render_profile).encode()
    signature = hashlib.sha256(signature_bytes).hexdigest()[:16]
    env['GAHYEON_LOOKING_GLASS_CACHE_DIR'] = str(ROOT / '.build/looking-glass-room-cache' / signature)
    return env

def process_group_alive(group: int) -> bool:
    # Darwin can return EPERM for a group containing only reaping zombies.
    rows = subprocess.run(['ps', '-axo', 'pgid=,stat='], check=True,
                          text=True, capture_output=True).stdout.splitlines()
    return any(len(parts := row.split()) == 2 and parts[0] == str(group)
               and not parts[1].startswith('Z') for row in rows)


def stop_process(process) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        # The launcher may exit before Unreal finishes shutdown. Wait for the
        # entire owned process group, including a renderer stuck in a crash dialog.
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            process.poll()
            if not process_group_alive(process.pid):
                process.wait(timeout=5)
                return
            time.sleep(.05)
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=5)
    except ProcessLookupError:
        pass
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()


def supervise_playback(runtime, stream, playback_ready: Path) -> int:
    while stream.poll() is None:
        if runtime is not None:
            if playback_ready.is_file():
                # The presenter has decoded and displayed a cached pose, and no
                # longer consumes the producer's IOSurface.
                stop_process(runtime)
                runtime = None
                print('GAHYEON_LKG_RENDERER_STOPPED cached_playback=1', flush=True)
            elif runtime.poll() is not None:
                raise RuntimeError('Renderer exited before cached playback')
        time.sleep(.25)
    return stream.returncode

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', required=True)
    parser.add_argument('--room-config', default='looking-glass-room-v011.json')
    parser.add_argument('--evidence-dir', default='artifacts/looking-glass-room-v006')
    parser.add_argument('--smooth', action='store_true', help='Cache 120 poses instead of 12; longer preparation')
    parser.add_argument('--check', action='store_true', help='Validate calibration and compile without launching Unreal')
    args = parser.parse_args()
    profile = display_profile(args.serial)
    env = environment(profile, canonical.load_manifest(), True, args.room_config)
    build()
    evidence = ROOT / args.evidence_dir
    evidence.mkdir(parents=True, exist_ok=True)
    env['GAHYEON_LOOKING_GLASS_CENTER_RGBA'] = str(evidence / 'center.rgba')
    print(json.dumps(dict(display=profile, map=env['GAHYEON_LOOKING_GLASS_RUNTIME_MAP'], mode='cached-idle-preview', frames=120)), flush=True)
    if args.check:
        return 0
    subprocess.run(['xcrun', 'metal', '--version'], check=True, capture_output=True)
    children = []
    def stop(*_):
        for process in reversed(children):
            stop_process(process)
    signal.signal(signal.SIGINT, lambda *_: sys.exit(130))
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    try:
        with tempfile.TemporaryDirectory(prefix='gahyeon-lg-') as tmp:
            playback_ready = Path(tmp) / 'playback-ready'
            env['GAHYEON_LOOKING_GLASS_PLAYBACK_READY_FILE'] = str(playback_ready)
            cache = Path(env['GAHYEON_LOOKING_GLASS_CACHE_DIR'])
            cache_ready = all((cache / f'pose-{i}.lz4').is_file() for i in range(120))
            runtime = None
            if cache_ready:
                # The presenter still checks cache sizes and decodes each pose.
                # A broken cache fails visibly; it never waits for a missing UE.
                env['GAHYEON_LOOKING_GLASS_CACHE_ONLY'] = '1'
            else:
                ready = Path(tmp) / 'ready'
                env['GAHYEON_RUNTIME_READY_FILE'] = str(ready)
                runtime = subprocess.Popen([sys.executable, str(ROOT / 'scripts/launch_canonical_macos_runtime.py')], cwd=ROOT, env=env, start_new_session=True)
                children.append(runtime)
                deadline = time.monotonic() + 120
                while not ready.exists():
                    if runtime.poll() is not None or time.monotonic() > deadline:
                        raise RuntimeError('Canonical renderer failed to become ready')
                    time.sleep(.1)
                time.sleep(30)
            stream = subprocess.Popen([str(BINARY)], cwd=ROOT, env=env, start_new_session=True)
            children.append(stream)
            return supervise_playback(runtime, stream, playback_ready)
    finally:
        stop()

if __name__ == '__main__':
    raise SystemExit(main())
