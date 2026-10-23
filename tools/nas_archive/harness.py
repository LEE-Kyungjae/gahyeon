#!/usr/bin/env python3
"""NAS archive CLI and stdio MCP. No third-party packages or embedded credentials."""
import argparse
import fcntl
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from urllib.parse import unquote

REPO = Path(__file__).resolve().parents[2]
CONFIG = REPO / 'config/storage/nas-archive.json'


def free_bytes(path):
    # macOS statvfs can truncate SMB block counts at 2**32; df uses statfs64.
    if sys.platform == 'darwin':
        line = subprocess.check_output(['/bin/df', '-Pk', str(path)], text=True).splitlines()[-1]
        return int(line.split()[3]) * 1024
    return shutil.disk_usage(path).free


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    with temp.open('w') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)


class ArchiveHarness:
    def __init__(self, repo=REPO, config=CONFIG):
        self.repo = Path(repo).resolve()
        self.config = json.loads(Path(config).read_text())
        self.mount = Path(self.config['mountPoint'])
        self.state = self.repo / 'artifacts/storage'
        self.state.mkdir(parents=True, exist_ok=True)

    def mounted(self):
        lines = subprocess.check_output(['/sbin/mount'], text=True).splitlines()
        for line in lines:
            if f' on {self.mount} (' in line and '(smbfs,' in line:
                source = unquote(line.split(' on ', 1)[0])
                if source.endswith('@' + self.config['host'] + '/' + self.config['share']):
                    return True
        return False

    def status(self):
        mounted = self.mounted()
        return {'mounted': mounted, 'mountPoint': str(self.mount),
                'nasFreeBytes': free_bytes(self.mount) if mounted else None,
                'localFreeBytes': free_bytes(self.repo),
                'plans': sorted(p.name.removesuffix('.plan.json') for p in self.state.glob('*.plan.json'))}

    def connect(self):
        if not self.mounted():
            result = subprocess.run(['bash', self.config['mountScript'], '--non-interactive'],
                                    capture_output=True, text=True, timeout=180)
            if result.returncode:
                raise RuntimeError('Existing NAS mount helper failed; credentials are not logged')
        self.require_mount()
        return self.status()

    def require_mount(self):
        if not self.mounted():
            raise RuntimeError('Expected SMB share is not mounted; refusing local fallback')
        root = self.mount / self.config['archiveSubdirectory']
        if root.is_symlink():
            raise RuntimeError('Archive root must not be a symlink')
        return root

    def safe_relative(self, relative):
        p = Path(relative)
        if p.is_absolute() or '..' in p.parts or str(p) in ('', '.'):
            raise ValueError('Invalid relative path')
        protected = list(self.config['protectedRoots'])
        canonical = self.repo / 'config/canonical-character-runtime.json'
        if canonical.exists():
            runtime = json.loads(canonical.read_text())['macos']
            for item in (str(Path(runtime['project']).parent), runtime['animationProfile']):
                absolute = (self.repo / item).resolve()
                if absolute.is_relative_to(self.repo):
                    protected.append(str(absolute.relative_to(self.repo)))
        if any(p == Path(x) or Path(x) in p.parents for x in protected):
            raise ValueError('Protected runtime/source path')
        if not any(p == Path(x) or Path(x) in p.parents for x in self.config['allowedRoots']):
            raise ValueError('Path outside archive allowlist')
        current = self.repo
        for part in p.parts:
            current = current / part
            if current.is_symlink():
                raise ValueError('Symlink source refused')
        return self.repo / p

    def tracked(self):
        out = subprocess.check_output(['git', 'ls-files', '-z'], cwd=self.repo)
        return set(out.decode().split('\0'))

    def plan_path(self, name):
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}', name):
            raise ValueError('Invalid plan ID')
        return self.state / (name + '.plan.json')

    def plan(self, name):
        target = self.plan_path(name)
        if target.exists():
            raise ValueError('Plan already exists; resume it instead')
        tracked = self.tracked()
        entries = []
        kept = []
        retained = []
        for relative in self.config['allowedRoots']:
            root = self.safe_relative(relative)
            for source in sorted(root.rglob('*')):
                rel = source.relative_to(self.repo).as_posix()
                self.safe_relative(rel)
                if not source.is_file():
                    continue
                if rel in tracked:
                    kept.append(rel)
                    continue
                if any(fnmatch.fnmatchcase(rel, pattern) for pattern in self.config.get('keepPatterns', [])):
                    retained.append(rel)
                    continue
                st = source.stat()
                entries.append({'path': rel, 'bytes': st.st_size, 'mtimeNs': st.st_mtime_ns})
        result = {'schemaVersion': 1, 'id': name, 'repo': str(self.repo),
                  'createdAt': time.time(), 'files': entries, 'keptTracked': kept, 'retainedMetadata': retained,
                  'bytes': sum(x['bytes'] for x in entries)}
        atomic_json(target, result)
        return {'plan': str(target), 'files': len(entries), 'bytes': result['bytes'], 'keptTracked': kept}

    def load(self, name):
        plan = json.loads(self.plan_path(name).read_text())
        if plan['repo'] != str(self.repo) or plan['id'] != name:
            raise ValueError('Plan identity mismatch')
        for row in plan['files']:
            self.safe_relative(row['path'])
        return plan

    def destination(self, name, relative):
        self.safe_relative(relative)
        root = self.require_mount() / name / 'files'
        dest = root / relative
        current = dest
        while current != self.mount:
            if current.is_symlink():
                raise ValueError('Symlink archive path refused')
            current = current.parent
        return dest

    def receipt_path(self, name, relative):
        key = hashlib.sha256(relative.encode()).hexdigest()
        return self.state / name / (key + '.json')

    def execute(self, name, prune=False):
        plan = self.load(name)
        root = self.require_mount() / name
        tracked = self.tracked()
        pending = sum(r['bytes'] for r in plan['files'] if not self.destination(name, r['path']).exists())
        if free_bytes(self.mount) < pending + 1024**3:
            raise RuntimeError('Insufficient NAS space including 1 GiB reserve')
        root.mkdir(parents=True, exist_ok=True)
        atomic_json(root / 'plan.json', plan)
        completed = 0
        freed = 0
        for row in plan['files']:
            relative = row['path']
            source = self.safe_relative(relative)
            dest = self.destination(name, relative)
            receipt_path = self.receipt_path(name, relative)
            previous = json.loads(receipt_path.read_text()) if receipt_path.exists() else None
            if not source.exists():
                if not previous or not dest.is_file() or digest(dest) != previous['sha256']:
                    raise RuntimeError('Missing source without verified archive: ' + relative)
                completed += 1
                continue
            if relative in tracked:
                raise RuntimeError('File became Git-tracked: ' + relative)
            before = source.stat()
            if before.st_size != row['bytes'] or before.st_mtime_ns != row['mtimeNs']:
                raise RuntimeError('Source changed since plan: ' + relative)
            expected = digest(source)
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                partial = dest.with_name(dest.name + '.partial')
                if partial.is_symlink():
                    raise RuntimeError('Symlink partial refused')
                with source.open('rb') as src, partial.open('wb') as dst:
                    shutil.copyfileobj(src, dst, 4 * 1024 * 1024)
                    dst.flush()
                    os.fsync(dst.fileno())
                if digest(partial) != expected:
                    raise RuntimeError('NAS checksum mismatch: ' + relative)
                os.replace(partial, dest)
            elif not dest.is_file() or digest(dest) != expected:
                raise RuntimeError('Existing archive differs; no overwrite: ' + relative)
            # Check source stability again immediately before recording/deleting.
            after = source.stat()
            if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
                raise RuntimeError('Source changed during copy: ' + relative)
            receipt = dict(row, sha256=expected, archive=str(dest), verifiedAt=time.time(), pruned=False)
            atomic_json(root / 'receipts' / receipt_path.name, receipt)
            atomic_json(receipt_path, receipt)
            if prune:
                self.require_mount()
                if relative in self.tracked() or digest(source) != expected:
                    raise RuntimeError('Source changed before prune: ' + relative)
                source.unlink()
                receipt['pruned'] = True
                atomic_json(receipt_path, receipt)
                atomic_json(root / 'receipts' / receipt_path.name, receipt)
                freed += row['bytes']
            completed += 1
            if completed % 25 == 0:
                print(json.dumps({'completed': completed, 'total': len(plan['files']), 'freedBytesThisRun': freed}), file=sys.stderr, flush=True)
        result = {'id': name, 'completed': completed, 'total': len(plan['files']),
                  'freedBytesThisRun': freed, 'archive': str(root), 'finishedAt': time.time()}
        atomic_json(self.state / (name + '.result.json'), result)
        atomic_json(root / 'result.json', result)
        return result

    def restore(self, name, relative):
        self.load(name)
        source = self.destination(name, relative)
        target = self.safe_relative(relative)
        receipt = json.loads(self.receipt_path(name, relative).read_text())
        expected = receipt['sha256']
        if not source.is_file() or digest(source) != expected:
            raise RuntimeError('Archive failed restore verification')
        if target.exists():
            if digest(target) != expected:
                raise RuntimeError('Restore would overwrite changed local file')
            return {'status': 'already-restored', 'path': str(target)}
        if free_bytes(self.repo) < receipt['bytes'] + 256 * 1024**2:
            raise RuntimeError('Insufficient local restore space')
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_name(target.name + '.restore-partial')
        if temp.exists() or temp.is_symlink():
            raise RuntimeError('Restore partial already exists')
        shutil.copyfile(source, temp)
        if digest(temp) != expected:
            raise RuntimeError('Restore checksum mismatch')
        os.utime(temp, ns=(receipt['mtimeNs'], receipt['mtimeNs']))
        os.replace(temp, target)
        return {'status': 'restored', 'path': str(target), 'sha256': expected}

    def dispatch(self, action, args):
        if action == 'status':
            return self.status()
        with (self.state / '.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if action == 'status': return self.status()
            if action == 'connect': return self.connect()
            if action == 'plan': return self.plan(args['name'])
            if action == 'execute':
                if not isinstance(args.get('prune', False), bool):
                    raise ValueError('prune must be a boolean')
                return self.execute(args['name'], args.get('prune', False))
            if action == 'restore': return self.restore(args['name'], args['path'])
            raise ValueError('Unknown action')


def mcp_server(harness):
    schemas = {
        'status': {}, 'connect': {}, 'plan': {'name': {'type': 'string'}},
        'execute': {'name': {'type': 'string'}, 'prune': {'type': 'boolean', 'default': False}},
        'restore': {'name': {'type': 'string'}, 'path': {'type': 'string'}}}
    descriptions = {
        'status': 'Read NAS mount identity, free space and archive plans.',
        'connect': 'Reconnect the existing NAS share using configured credentials.',
        'plan': 'Create an archive inventory; excludes Git-tracked and protected runtime files.',
        'execute': 'Copy and SHA-256 verify a plan. prune=true removes verified local originals; requires user archive authorization.',
        'restore': 'Restore one archived file by receipt; refuses overwrite of changed files.'}
    for line in sys.stdin:
        request = {}
        try:
            request = json.loads(line)
            method = request['method']
            if 'id' not in request: continue
            if method == 'initialize':
                result = {'protocolVersion': '2024-11-05', 'capabilities': {'tools': {}},
                          'serverInfo': {'name': 'gahyeon-nas-archive', 'version': '1.0.0'}}
            elif method == 'ping': result = {}
            elif method == 'tools/list':
                result = {'tools': [{'name': 'nas_' + key, 'description': descriptions[key],
                          'inputSchema': {'type': 'object', 'properties': props,
                          'required': [k for k in props if k != 'prune'], 'additionalProperties': False}}
                          for key, props in schemas.items()]}
            elif method == 'tools/call':
                params = request['params']
                try:
                    value = harness.dispatch(params['name'].removeprefix('nas_'), params.get('arguments', {}))
                    result = {'content': [{'type': 'text', 'text': json.dumps(value, ensure_ascii=False)}]}
                except Exception as exc:
                    result = {'isError': True, 'content': [{'type': 'text', 'text': str(exc)}]}
            else: raise ValueError('Unsupported method')
            response = {'jsonrpc': '2.0', 'id': request['id'], 'result': result}
        except Exception as exc:
            response = {'jsonrpc': '2.0', 'id': request.get('id'), 'error': {'code': -32603, 'message': str(exc)}}
        print(json.dumps(response, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['status', 'connect', 'plan', 'execute', 'restore', 'mcp'])
    parser.add_argument('--name')
    parser.add_argument('--path')
    parser.add_argument('--prune', action='store_true')
    args = parser.parse_args()
    harness = ArchiveHarness()
    if args.action == 'mcp':
        mcp_server(harness)
    else:
        print(json.dumps(harness.dispatch(args.action, vars(args)), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
