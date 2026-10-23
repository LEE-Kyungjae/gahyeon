"""Connect the native desktop to the existing zeze production service, without deployment."""
import base64
import ipaddress
import json
import os
from pathlib import Path
import subprocess
try:
    from .macos_core_connection import available_port, speech_status
except ImportError:
    from macos_core_connection import available_port, speech_status


def connect_production_core(directory=None):
    explicit = os.environ.get('GAHYEON_CORE_URL')
    if explicit:
        token = os.environ.get('GAHYEON_CLIENT_TOKEN', '')
        if not token:
            raise RuntimeError('Explicit Core URL requires its own client credential')
        return explicit, token, speech_status(explicit, token)
    ssh = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8', 'zeze']
    encoded = subprocess.check_output(ssh + [
        'kubectl -n gahyeonbot get secret gahyeonbot-secrets -o jsonpath="{.data.GAHYEON_CLIENT_TOKEN}"'
    ], text=True, timeout=15).strip()
    token = base64.b64decode(encoded, validate=True).decode().strip()
    if not token:
        raise RuntimeError('Production desktop credential is empty')
    service_ip = subprocess.check_output(ssh + [
        'kubectl -n gahyeonbot get service gahyeonbot -o jsonpath="{.spec.clusterIP}"'
    ], text=True, timeout=15).strip()
    ipaddress.IPv4Address(service_ip)
    directory = Path(directory or Path.home() / '.cache/gahyeon')
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    state = directory / 'zeze-core-connection.json'
    control = directory / 'zeze-core-ssh'
    if state.is_file() and control.exists():
        prior = json.loads(state.read_text())
        check = subprocess.run(ssh[:-1] + ['-S', str(control), '-O', 'check', 'zeze'], capture_output=True, timeout=10)
        port = prior.get('port')
        if check.returncode == 0 and prior.get('serviceIp') == service_ip and type(port) is int and 1024 <= port <= 65535:
            url = f'http://127.0.0.1:{port}/api'
            return url, token, speech_status(url, token)
        if check.returncode == 0:
            subprocess.run(ssh[:-1] + ['-S', str(control), '-O', 'exit', 'zeze'], check=True, capture_output=True, timeout=10)
    port = available_port(18082)
    subprocess.run(ssh[:-1] + ['-fNT', '-M', '-S', str(control), '-o', 'ExitOnForwardFailure=yes',
        '-o', 'ServerAliveInterval=15', '-o', 'ServerAliveCountMax=3', '-L',
        f'127.0.0.1:{port}:{service_ip}:8080', 'zeze'], check=True, timeout=15)
    state.write_text(json.dumps({'port':port, 'serviceIp':service_ip})+'\n')
    url = f'http://127.0.0.1:{port}/api'
    return url, token, speech_status(url, token)
