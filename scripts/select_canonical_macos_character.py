#!/usr/bin/env python3
"""Select an installed roster model through the existing canonical Unreal launcher."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def prepare_selection(character_id, root=ROOT):
    roster = json.loads((root / 'config/character-model-roster.json').read_text())
    matches = [c for c in roster['characters'] if c['id'] == character_id]
    if len(matches) != 1:
        raise ValueError('Unknown character model')
    selected = matches[0]
    manifest_path = root / 'config/canonical-character-runtime.json'
    manifest = json.loads(manifest_path.read_text())
    if manifest.get('runtime') != 'unreal' or manifest.get('status') != 'ready':
        raise ValueError('Canonical Unreal runtime is not ready')
    project = (root / manifest['macos']['project']).parent
    for key, suffix in [('runtimeMap', '.umap'), ('characterAsset', '.uasset')]:
        asset = selected[key]
        if not asset.startswith('/Game/') or '..' in asset.split('/'):
            raise ValueError('Invalid Unreal asset path')
        if not (project / 'Content' / (asset[6:] + suffix)).is_file():
            raise ValueError('Character asset is not installed: ' + asset)
    profile = root / selected['animationProfile']
    if not profile.is_file():
        raise ValueError('Missing animation profile')
    source = root / selected['source']
    if hashlib.sha256(source.read_bytes()).hexdigest() != selected['sourceSha256']:
        raise ValueError('Character source hash differs')
    for key in ('runtimeMap', 'characterAsset', 'animationProfile'):
        manifest['macos'][key] = selected[key]
    manifest['macos']['characterModelId'] = selected['id']
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('character_id')
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    if platform.system() != 'Darwin':
        raise RuntimeError('macOS only')
    with (ROOT / 'config/.character-selection.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        manifest = prepare_selection(args.character_id)
        if args.check_only:
            print(json.dumps({'id': args.character_id, 'installed': True}))
            return
        folder = ROOT / 'artifacts/land-characters/roster-20261016'
        stamp = str(time.time_ns())
        target = ROOT / 'config/canonical-character-runtime.json'
        prior = target.read_bytes()
        (folder / ('runtime-before-' + stamp + '.json')).write_bytes(prior)
        temporary = target.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
        os.replace(temporary, target)
        ready = folder / ('launch-' + stamp + '.ready')
        with (folder / ('launch-' + stamp + '.log')).open('w') as log:
            process = subprocess.Popen([sys.executable, str(ROOT / 'scripts/launch_canonical_macos_runtime.py')],
                cwd=ROOT, env=dict(os.environ, GAHYEON_RUNTIME_READY_FILE=str(ready)),
                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        deadline = time.monotonic() + 30
        while not ready.exists():
            if process.poll() is not None or time.monotonic() > deadline:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                target.write_bytes(prior)
                raise RuntimeError('Canonical launch failed; previous selection restored')
            time.sleep(0.1)
        print(json.dumps({'id': args.character_id, 'launcherPid': process.pid, 'visualApproved': False}))


if __name__ == '__main__':
    main()
