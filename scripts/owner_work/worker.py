#!/usr/bin/env python3
"""One JSON request per forced SSH connection; fixed workspace, no shell tool.
The dedicated SSH key holder is the trusted broker, not an end-user credential.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import signal
import subprocess
import sys
import tempfile
import time

LIMIT = 48000
DENIED = {'.git', '.ssh', '.aws', '.kube', '.config', '.env', '.npmrc', '.pypirc',
          'credentials', 'secrets', 'id_rsa', 'id_ed25519', 'node_modules', '.gradle'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_path(root, value, writing=False):
    if not isinstance(value, str) or not value or len(value) > 512:
        raise ValueError('invalid_path')
    path = Path(value)
    if path.is_absolute() or '..' in path.parts or not path.parts:
        raise ValueError('path_escape')
    for part in path.parts:
        low = part.lower()
        if low in DENIED or low.startswith('.env') or low.endswith(('.pem', '.key', '.p12', '.jks')):
            raise ValueError('protected_path')
    current = root
    for part in path.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('symlink_denied')
    if not current.resolve().is_relative_to(root):
        raise ValueError('path_escape')
    if writing and not current.parent.is_dir():
        raise ValueError('parent_missing')
    if current.exists() and current.is_file() and current.stat().st_nlink != 1:
        raise ValueError('hardlink_denied')
    return current


def bounded_process(command, cwd):
    env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'HOME': '/tmp', 'LANG': 'C.UTF-8'}
    process = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
    output = bytearray()
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            deadline = time.monotonic() + 60
            while selector.get_map():
                if time.monotonic() >= deadline:
                    raise ValueError('test_timeout')
                for key, _ in selector.select(.2):
                    chunk = os.read(key.fileobj.fileno(), 8192)
                    if not chunk:
                        selector.unregister(key.fileobj)
                    else:
                        output.extend(chunk)
                        if len(output) > LIMIT:
                            raise ValueError('test_output_limit')
            code = process.wait(timeout=2)
            return {'exitCode': code, 'output': output.decode('utf-8', errors='replace')}
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        process.stdout.close()


def sandbox_command(root, config):
    command = config.get('testCommand')
    if not isinstance(command, list) or not command or not all(isinstance(x, str) for x in command):
        raise ValueError('test_not_configured')
    if sys.platform == 'darwin':
        if not Path('/usr/bin/sandbox-exec').exists():
            raise ValueError('sandbox_unavailable')
        profile = '(version 1)(deny default)(import "dyld-support.sb")(allow syscall*)(allow mach-bootstrap)(allow file-read-metadata)(allow process-exec)(allow process-fork)(allow sysctl-read)'
        for path in ['/System', '/usr', '/bin', '/sbin', '/Library/Apple', '/Applications/Xcode.app', '/Library/Developer/CommandLineTools', '/dev/null', '/dev/urandom']:
            profile += '(allow file-read* file-map-executable (subpath ' + json.dumps(path) + '))'
        profile += '(allow file-read* file-write* (subpath ' + json.dumps(str(root)) + '))'
        profile += '(allow file-write* (literal "/dev/null"))'
        return ['/usr/bin/sandbox-exec', '-p', profile, *command]
    bwrap = Path('/usr/bin/bwrap')
    if not bwrap.exists():
        raise ValueError('sandbox_unavailable')
    result = [str(bwrap), '--die-with-parent', '--new-session', '--unshare-all', '--clearenv',
              '--setenv', 'PATH', '/usr/bin:/bin', '--setenv', 'HOME', '/tmp',
              '--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp']
    for path in ['/usr', '/bin', '/lib', '/lib64']:
        if Path(path).exists():
            result += ['--ro-bind', path, path]
    return result + ['--bind', str(root), str(root), '--chdir', str(root), '--', *command]


def execute_task(root, task, config):
    if not isinstance(task, dict) or set(task) - {'target', 'action', 'path', 'content', 'expectedSha256'}:
        raise ValueError('invalid_task')
    if task.get('target') != config['target']:
        raise ValueError('wrong_target')
    action = task.get('action')
    if action == 'status':
        return {'target': config['target'], 'workspace': str(root), 'testConfigured': bool(config.get('testCommand'))}
    if action == 'list':
        return {'files': sorted(p.name for p in root.iterdir() if not p.is_symlink()
                               and p.name.lower() not in DENIED and not p.name.startswith('.'))[:200]}
    if action == 'test':
        return bounded_process(sandbox_command(root, config), root)
    if action not in {'read', 'write'}:
        raise ValueError('unknown_action')
    path = safe_path(root, task.get('path'), action == 'write')
    if path.exists() and (not path.is_file() or path.stat().st_size > LIMIT):
        raise ValueError('file_size_or_type')
    data = path.read_bytes() if path.exists() else b''
    if action == 'read':
        if not path.exists():
            raise ValueError('file_missing')
        return {'path': task['path'], 'sha256': digest(data), 'content': data.decode('utf-8')}
    content = task.get('content')
    if not isinstance(content, str) or len(content.encode('utf-8')) > LIMIT:
        raise ValueError('invalid_content')
    if task.get('expectedSha256') != (digest(data) if path.exists() else 'absent'):
        raise ValueError('file_changed')
    descriptor, name = tempfile.mkstemp(dir=path.parent, prefix='.gahyeon-write-')
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(content.encode('utf-8')); stream.flush(); os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)
    return {'path': task['path'], 'sha256': digest(path.read_bytes()), 'bytes': path.stat().st_size}


def handle(config, request):
    if not isinstance(request, dict) or set(request) != {'actor', 'scope', 'jobId', 'task'}:
        raise ValueError('invalid_envelope')
    if str(config.get('ownerActor', '')) in {'', '0'} or str(config.get('scope', '')) in {'', '0'}:
        raise ValueError('owner_not_configured')
    if request['actor'] != str(config['ownerActor']) or request['scope'] != str(config['scope']):
        raise ValueError('unauthorized')
    job = request['jobId']
    if not isinstance(job, str) or not re.fullmatch('[a-f0-9]{64}', job):
        raise ValueError('invalid_job_id')
    root = Path(config['workspace']).resolve(strict=True)
    state = Path(config['stateDir']).resolve(strict=True)
    if state.is_relative_to(root) or root == Path.home() or root == Path('/'):
        raise ValueError('unsafe_workspace')
    identity = digest(json.dumps(request, sort_keys=True).encode())
    with (state / 'worker.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        record = state / (job + '.json')
        if record.exists():
            prior = json.loads(record.read_text())
            if prior['identity'] != identity:
                raise ValueError('job_id_reused')
            if 'result' not in prior:
                raise ValueError('interrupted_job_requires_review')
            return prior['result']
        record.write_text(json.dumps({'identity': identity})); os.chmod(record, 0o600)
        try:
            payload = execute_task(root, request['task'], config)
            result = {'ok': payload.get('exitCode', 0) == 0, 'jobId': job, 'result': payload}
        except (ValueError, OSError, UnicodeError, subprocess.SubprocessError) as error:
            result = {'ok': False, 'jobId': job, 'error': str(error)[:100]}
        record.write_text(json.dumps({'identity': identity, 'result': result}))
        return result


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--config', required=True)
    args = parser.parse_args()
    try:
        config_path = Path(args.config)
        if config_path.stat().st_mode & 0o022:
            raise ValueError('writable_config')
        config = json.loads(config_path.read_text())
        raw = sys.stdin.buffer.readline(65537)
        if len(raw) > 65536:
            raise ValueError('request_too_large')
        print(json.dumps(handle(config, json.loads(raw)), ensure_ascii=False))
    except Exception as error:
        print(json.dumps({'ok': False, 'error': type(error).__name__})); return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
