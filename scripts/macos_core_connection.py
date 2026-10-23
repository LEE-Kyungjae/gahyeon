"""Own the SSH forwarding endpoint instead of trusting any open local port."""
import json
import os
from pathlib import Path
import socket
import subprocess
import urllib.request


def speech_status(url, token):
    request = urllib.request.Request(url.rstrip('/') + '/gahyeon/desktop/speech/status',
                                     headers={'Authorization': 'Bearer ' + token})
    with urllib.request.urlopen(request, timeout=10) as response:
        result = json.load(response)
    if not isinstance(result, dict) or any(type(result.get(k)) is not bool for k in
                                          ('transcriptionReady', 'synthesisReady')):
        raise RuntimeError('Endpoint is not the Gahyeon speech service')
    return result


def available_port(preferred=18081):
    with socket.socket() as candidate:
        try:
            candidate.bind(('127.0.0.1', preferred))
        except OSError:
            candidate.bind(('127.0.0.1', 0))
        return candidate.getsockname()[1]


def connect_land_core(token, directory=None):
    explicit = os.environ.get('GAHYEON_CORE_URL')
    if explicit:
        return explicit, speech_status(explicit, token)
    directory = Path(directory or Path.home() / '.cache/gahyeon')
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    state = directory / 'land-core-connection.json'
    control = directory / 'land-core-ssh'
    if state.is_file() and control.exists():
        previous = json.loads(state.read_text())
        check = subprocess.run(['ssh', '-S', str(control), '-O', 'check', 'land'],
                               capture_output=True)
        port = previous.get('port')
        if check.returncode == 0 and type(port) is int and 1024 <= port <= 65535:
            url = f'http://127.0.0.1:{port}/api'
            return url, speech_status(url, token)
    port = available_port()
    # ExitOnForwardFailure fails closed if another process wins the bind race.
    subprocess.run(['ssh', '-fNT', '-M', '-S', str(control), '-o', 'BatchMode=yes',
                    '-o', 'ExitOnForwardFailure=yes', '-o', 'ServerAliveInterval=15',
                    '-o', 'ServerAliveCountMax=3', '-L',
                    f'127.0.0.1:{port}:127.0.0.1:18080', 'land'], check=True)
    state.write_text(json.dumps({'port': port}) + '\n')
    url = f'http://127.0.0.1:{port}/api'
    return url, speech_status(url, token)
