#!/usr/bin/env python3
"""Connect the canonical macOS runtime to the existing production Core through SSH."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import urllib.request

root = Path(__file__).resolve().parents[1]
# Production is zeze. land remains an explicitly selected development backend.
target = os.environ.get('GAHYEON_CORE_TARGET', 'zeze')
if target not in {'zeze', 'land'}: raise SystemExit('Unknown Core target')
if target == 'land':
    token = os.environ.get('GAHYEON_CLIENT_TOKEN') or subprocess.check_output([
        'ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8', 'land',
        'cat /home/ubuntu/.config/gahyeon/client-token',
    ], text=True, timeout=15).strip()
    if not token: raise SystemExit('Core client credential is empty')
    from macos_core_connection import connect_land_core
    url, status = connect_land_core(token)
else:
    from macos_production_core import connect_production_core
    url, token, status = connect_production_core()
print(json.dumps({'coreConnected': True, 'speech': status}), flush=True)
env = dict(os.environ, GAHYEON_CORE_URL=url, GAHYEON_CLIENT_TOKEN=token)
os.execve(sys.executable, [sys.executable, str(root / 'scripts/launch_canonical_macos_runtime.py')], env)
