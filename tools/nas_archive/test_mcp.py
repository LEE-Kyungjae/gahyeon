import fcntl
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch
import test_harness as fixtures

m = fixtures.m


class HarnessControlTests(unittest.TestCase):
    setUp = fixtures.ArchiveTests.setUp
    tearDown = fixtures.ArchiveTests.tearDown

    def test_status_returns_usable_plan_ids(self):
        self.h.plan('run')
        self.assertEqual(self.h.status()['plans'], ['run'])

    def test_newly_selected_runtime_is_protected(self):
        self.h.plan('run')
        config = self.repo / 'config'
        config.mkdir()
        (config / 'canonical-character-runtime.json').write_text(json.dumps({
            'macos': {'project': 'old/new-runtime.uproject', 'animationProfile': 'config/animation.json'}}))
        with self.assertRaises(ValueError): self.h.execute('run', prune=True)
        self.assertTrue(self.file.exists())

    def test_retains_nested_reports(self):
        self.h.config['keepPatterns'] = ['old/*.json']
        directory = self.repo / 'old/nested'
        directory.mkdir()
        (directory / 'report.json').write_text('{}')
        self.h.plan('run')
        self.h.execute('run', prune=True)
        self.assertTrue((directory / 'report.json').exists())
        self.assertFalse(self.file.exists())

    def test_status_during_mutation_lock(self):
        with (self.h.state / '.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertTrue(self.h.dispatch('status', {})['mounted'])
            with self.assertRaises(BlockingIOError): self.h.dispatch('plan', {'name': 'other'})

    def test_prune_requires_boolean(self):
        with self.assertRaises(ValueError): self.h.dispatch('execute', {'name': 'run', 'prune': 'false'})

    def test_space_shortage_preserves_source(self):
        self.h.plan('run')
        with patch.object(m, 'free_bytes', return_value=1):
            with self.assertRaises(RuntimeError): self.h.execute('run', prune=True)
        self.assertTrue(self.file.exists())

    def test_stdio_protocol(self):
        messages = [
          {'jsonrpc':'2.0', 'id':1, 'method':'initialize', 'params':{'protocolVersion':'2024-11-05'}},
          {'jsonrpc':'2.0', 'method':'notifications/initialized'},
          {'jsonrpc':'2.0', 'id':2, 'method':'tools/list'},
          {'jsonrpc':'2.0', 'id':3, 'method':'tools/call', 'params':{'name':'nas_missing'}},
        ]
        result = subprocess.run(['python3', str(Path(__file__).with_name('harness.py')), 'mcp'],
          input='\n'.join(json.dumps(x) for x in messages)+'\n', text=True, capture_output=True, check=True)
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(len(responses), 3)
        self.assertEqual(responses[0]['result']['serverInfo']['name'], 'gahyeon-nas-archive')
        self.assertEqual(len(responses[1]['result']['tools']), 5)
        self.assertTrue(responses[2]['result']['isError'])
