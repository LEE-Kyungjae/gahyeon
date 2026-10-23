import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import worker


class WorkerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve()
        self.root = self.base / 'workspace'; self.root.mkdir()
        self.state = self.base / 'state'; self.state.mkdir(mode=0o700)
        self.config = dict(ownerActor='42', scope='7', target='mac', workspace=str(self.root), stateDir=str(self.state))
        self.serial = 0

    def tearDown(self):
        self.tmp.cleanup()

    def request(self, action, **kwargs):
        self.serial += 1
        return dict(actor='42', scope='7', jobId=hashlib.sha256(str(self.serial).encode()).hexdigest(),
                    task=dict(target='mac', action=action, **kwargs))

    def test_owner_and_scope_cannot_be_supplied_by_task(self):
        for field in ['actor', 'scope']:
            request = self.request('status'); request[field] = '99'
            with self.assertRaisesRegex(ValueError, 'unauthorized'):
                worker.handle(self.config, request)
        request = self.request('status', actor='42')
        self.assertFalse(worker.handle(self.config, request)['ok'])

    def test_path_escape_symlink_hardlink_and_secrets_are_blocked(self):
        outside = self.base / 'private'; outside.write_text('private')
        (self.root / 'link').symlink_to(outside)
        os.link(outside, self.root / 'hard')
        for path in ['../private', str(outside), 'link', 'hard', '.ssh/key', '.env.local', 'token.pem']:
            result = worker.handle(self.config, self.request('read', path=path))
            self.assertFalse(result['ok'], path)
            self.assertNotIn('private', json.dumps(result.get('result', {})))

    def test_write_read_hash_conflict_and_replay(self):
        request = self.request('write', path='code.py', content='answer = 42\n', expectedSha256='absent')
        result = worker.handle(self.config, request)
        self.assertTrue(result['ok'])
        self.assertEqual(worker.handle(self.config, request), result)
        read = worker.handle(self.config, self.request('read', path='code.py'))
        self.assertEqual(read['result']['content'], 'answer = 42\n')
        failed = worker.handle(self.config, self.request('write', path='code.py',content='bad',expectedSha256='absent'))
        self.assertFalse(failed['ok'])
        request['task']['content'] = 'different'
        with self.assertRaisesRegex(ValueError, 'job_id_reused'):
            worker.handle(self.config, request)

    def test_interrupted_job_never_reexecutes(self):
        request = self.request('write', path='code.py', content='x', expectedSha256='absent')
        identity = worker.digest(json.dumps(request, sort_keys=True).encode())
        (self.state / (request['jobId'] + '.json')).write_text(json.dumps(dict(identity=identity)))
        with self.assertRaisesRegex(ValueError, 'interrupted_job_requires_review'):
            worker.handle(self.config, request)
        self.assertFalse((self.root / 'code.py').exists())

    def test_missing_sandbox_never_runs_unrestricted(self):
        self.config['testCommand'] = ['/usr/bin/true']
        with patch.object(worker.sys, 'platform', 'linux'), patch.object(worker.Path, 'exists', return_value=False):
            with self.assertRaisesRegex(ValueError, 'sandbox_unavailable'):
                worker.sandbox_command(self.root, self.config)

    def test_shell_and_other_target_are_rejected(self):
        self.assertFalse(worker.handle(self.config, self.request('shell'))['ok'])
        request = self.request('status'); request['task']['target'] = 'zeze'
        self.assertFalse(worker.handle(self.config, request)['ok'])

    @unittest.skipUnless(sys.platform == 'darwin' or Path('/usr/bin/bwrap').exists(), 'OS sandbox integration')
    def test_real_sandbox_denies_outside_read_write_and_network(self):
        outside = self.base / 'secret.txt'; outside.write_text('private')
        code = '''import pathlib, socket, sys
root = pathlib.Path(__file__).parent
(root / 'allowed.txt').write_text('worked')
for path in [root.parent / 'secret.txt', pathlib.Path.home() / '.ssh' / 'id_ed25519']:
    try:
        path.read_text()
    except (PermissionError, FileNotFoundError):
        pass
    else:
        raise AssertionError('outside read allowed')
try:
    (root.parent / 'escape.txt').write_text('escape')
except (PermissionError, FileNotFoundError):
    pass
else:
    if sys.platform == 'darwin':
        raise AssertionError('outside write allowed')
    # Linux /tmp is an isolated tmpfs; the host is checked after execution.
try:
    socket.create_connection(('127.0.0.1', 22), timeout=1)
except OSError as error:
    if sys.platform == 'darwin' and not isinstance(error, PermissionError):
        raise
else:
    raise AssertionError('network allowed')
print('sandbox checks passed')
'''
        (self.root / 'test_security.py').write_text(code)
        self.config['testCommand'] = [sys.executable, '-I', str(self.root / 'test_security.py')]
        result = worker.handle(self.config, self.request('test'))
        self.assertTrue(result['ok'], result)
        self.assertIn('sandbox checks passed', result['result']['output'])
        self.assertEqual((self.root / 'allowed.txt').read_text(), 'worked')
        self.assertFalse((self.base / 'escape.txt').exists())


if __name__ == '__main__':
    unittest.main()
