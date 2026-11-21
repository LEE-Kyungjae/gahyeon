"""Portrait cache identity and renderer lifetime regressions."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import test_looking_glass_room_clarity as baseline
import launch_gahyeon_looking_glass_room_v011 as room


class PortraitEnvironmentTests(baseline.RoomEnvironmentTests):
    def test_profile_changes_cache_without_changing_scene(self):
        before = room.environment(self.profile, self.manifest, True)
        self.scene['renderProfile'] = 'portrait-v001'
        self.save_scene()
        after = room.environment(self.profile, self.manifest, True)
        self.assertNotEqual(before['GAHYEON_LOOKING_GLASS_CACHE_DIR'], after['GAHYEON_LOOKING_GLASS_CACHE_DIR'])
        self.assertEqual(before['GAHYEON_LOOKING_GLASS_RUNTIME_MAP'], after['GAHYEON_LOOKING_GLASS_RUNTIME_MAP'])
        self.assertEqual(after['GAHYEON_LOOKING_GLASS_RENDER_PROFILE'], 'portrait-v001')

    def test_ram_cap_is_bounded_and_does_not_invalidate_quilts(self):
        before = room.environment(self.profile, self.manifest, True)
        self.scene['compressedCacheMiB'] = 1792
        self.save_scene()
        after = room.environment(self.profile, self.manifest, True)
        self.assertEqual(before['GAHYEON_LOOKING_GLASS_CACHE_DIR'], after['GAHYEON_LOOKING_GLASS_CACHE_DIR'])
        self.assertEqual(after['GAHYEON_LOOKING_GLASS_COMPRESSED_CACHE_MIB'], '1792')
        for invalid in (-1, 1793, 1.5, True):
            self.scene['compressedCacheMiB'] = invalid
            self.save_scene()
            with self.assertRaises(ValueError):
                room.environment(self.profile, self.manifest, True)

    def test_unknown_profile_rejected(self):
        self.scene['renderProfile'] = 'typo'
        self.save_scene()
        with self.assertRaises(ValueError):
            room.environment(self.profile, self.manifest, True)


class PlaybackLifetimeTests(unittest.TestCase):
    def test_renderer_stops_only_after_presenter_handshake(self):
        with tempfile.TemporaryDirectory() as tmp:
            ready = Path(tmp) / 'playing'
            runtime = Mock(poll=Mock(return_value=None))
            stream = Mock(poll=Mock(side_effect=[None, None, None, 0]), returncode=0)
            ticks = []
            def advance(_):
                ticks.append(1)
                if len(ticks) == 1:
                    stop.assert_not_called()
                    ready.write_text('playing\n')
            with patch.object(room, 'stop_process') as stop, patch.object(room.time, 'sleep', side_effect=advance):
                self.assertEqual(room.supervise_playback(runtime, stream, ready), 0)
                stop.assert_called_once_with(runtime)

    def test_failed_renderer_is_not_mistaken_for_cache_transition(self):
        runtime = Mock(poll=Mock(return_value=7))
        stream = Mock(poll=Mock(return_value=None))
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError, 'before cached playback'):
                room.supervise_playback(runtime, stream, Path(tmp) / 'missing')

    def test_cache_only_mode_propagates_presenter_failure(self):
        stream = Mock(poll=Mock(return_value=9), returncode=9)
        with patch.object(room, 'stop_process') as stop:
            self.assertEqual(room.supervise_playback(None, stream, Path('unused')), 9)
            stop.assert_not_called()

    def test_shutdown_reaps_renderer_after_launcher_exits(self):
        import subprocess
        import sys
        import os
        child_code = "import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); print('ready',flush=True); time.sleep(60)"
        parent_code = "import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',sys.argv[1]]); time.sleep(60)"
        process = subprocess.Popen([sys.executable, '-c', parent_code, child_code],
                                   stdout=subprocess.PIPE, text=True, start_new_session=True)
        try:
            self.assertEqual(process.stdout.readline().strip(), 'ready')
            room.stop_process(process)
            # Orphan reaping can lag the KILL by a scheduling turn on macOS.
            import time
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                if not room.process_group_alive(process.pid):
                    break
                time.sleep(.05)
            else:
                self.fail('Owned renderer process group survived shutdown')
        finally:
            if room.process_group_alive(process.pid):
                os.killpg(process.pid, 9)
            process.wait()
            process.stdout.close()

    def test_finished_process_is_never_signalled_again(self):
        process = Mock(poll=Mock(return_value=0))
        with patch.object(room.os, 'killpg') as kill:
            room.stop_process(process)
            kill.assert_not_called()

class PortraitViewportTests(unittest.TestCase):
    def test_portrait_dimensions_do_not_change_other_launch_modes(self):
        import os
        import launch_canonical_macos_runtime as canonical
        manifest = dict(status='ready', macos=dict(engineRoot='/engine', project='scene.uproject', runtimeMap='/Game/Room'))
        for enabled, profile, dimensions in [(True, 'portrait-v001', (252, 448)), (True, 'tile-v001', (800, 629)), (False, 'portrait-v001', (1600, 1258))]:
            with self.subTest(enabled=enabled, profile=profile), patch.object(canonical.platform, 'system', return_value='Darwin'), patch.object(Path, 'is_file', return_value=True), patch.dict(os.environ, {'GAHYEON_LOOKING_GLASS_QUILT': str(int(enabled)), 'GAHYEON_LOOKING_GLASS_RENDER_PROFILE': profile}, clear=True):
                command = canonical.build_command(manifest)
                self.assertIn(f'-ResX={dimensions[0]}', command)
                self.assertIn(f'-ResY={dimensions[1]}', command)
                if enabled:
                    self.assertIn('r.ScreenPercentage 100', ','.join(command))


if __name__ == '__main__':
    unittest.main()
