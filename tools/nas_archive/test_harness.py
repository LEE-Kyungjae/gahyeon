import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('nas_harness', Path(__file__).with_name('harness.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        self.nas = self.root / 'nas'
        self.nas.mkdir()
        config = self.root / 'config.json'
        config.write_text(json.dumps({'mountPoint': str(self.nas), 'host': 'test', 'share': 'data',
          'archiveSubdirectory': 'archive', 'allowedRoots': ['old'], 'protectedRoots': ['runtime']}))
        self.h = m.ArchiveHarness(self.repo, config)
        self.patcher = patch.object(self.h, 'mounted', return_value=True)
        self.patcher.start()
        # Temp fixtures share the nearly-full local disk, not a real NAS.
        space = patch.object(m, 'free_bytes', return_value=100 * 1024**3)
        space.start()
        self.addCleanup(space.stop)
        (self.repo / 'old').mkdir()
        self.file = self.repo / 'old/한글.blend'
        self.file.write_bytes(b'original character\x00' * 100)

    def tearDown(self):
        self.patcher.stop()
        self.temp.cleanup()

    def test_copy_prune_restore_and_idempotent_resume(self):
        expected = self.file.read_bytes()
        self.h.plan('run')
        self.h.execute('run')
        self.assertTrue(self.file.exists())
        self.h.execute('run', prune=True)
        self.assertFalse(self.file.exists())
        self.h.execute('run', prune=True)
        self.h.restore('run', 'old/한글.blend')
        self.assertEqual(self.file.read_bytes(), expected)

    def test_corrupt_destination_never_prunes(self):
        self.h.plan('run')
        self.h.execute('run')
        self.h.destination('run', 'old/한글.blend').write_bytes(b'corrupt')
        with self.assertRaises(RuntimeError): self.h.execute('run', prune=True)
        self.assertTrue(self.file.exists())
        with self.assertRaises(RuntimeError): self.h.restore('run', 'old/한글.blend')

    def test_changed_source_never_prunes(self):
        self.h.plan('run')
        self.file.write_bytes(b'new work')
        with self.assertRaises(RuntimeError): self.h.execute('run', prune=True)
        self.assertEqual(self.file.read_bytes(), b'new work')

    def test_git_tracked_excluded(self):
        subprocess.run(['git', 'add', '.'], cwd=self.repo, check=True)
        self.assertEqual(self.h.plan('run')['files'], 0)

    def test_paths_and_symlinks_rejected(self):
        for path in ['../secret', '/etc/passwd', 'runtime/a', 'unlisted/a']:
            with self.assertRaises(ValueError): self.h.destination('run', path)
        (self.repo / 'old/link').symlink_to(self.root)
        with self.assertRaises(ValueError): self.h.plan('run')

    def test_disconnected_nas_never_writes_local_fallback(self):
        self.h.plan('run')
        with patch.object(self.h, 'mounted', return_value=False):
            with self.assertRaises(RuntimeError): self.h.execute('run', prune=True)
        self.assertTrue(self.file.exists())
        self.assertFalse((self.nas / 'archive').exists())

    def test_restore_preserves_new_local_work(self):
        self.h.plan('run')
        self.h.execute('run')
        self.file.write_bytes(b'new work')
        with self.assertRaises(RuntimeError): self.h.restore('run', 'old/한글.blend')
        self.assertEqual(self.file.read_bytes(), b'new work')

    def test_source_changed_during_copy_preserved(self):
        self.h.plan('run')
        original = m.shutil.copyfileobj
        def mutate(src, dst, length):
            original(src, dst, length)
            self.file.write_bytes(b'changed during archive')
        with patch.object(m.shutil, 'copyfileobj', side_effect=mutate):
            with self.assertRaises(RuntimeError): self.h.execute('run', prune=True)
        self.assertEqual(self.file.read_bytes(), b'changed during archive')


if __name__ == '__main__': unittest.main()
