"""Capture geometry changes must not replay a cache from another baseline."""
import hashlib
import json
import test_looking_glass_room_clarity as baseline
import launch_gahyeon_looking_glass_room_v011 as room


class CaptureDepthTests(baseline.RoomEnvironmentTests):
    def test_default_preserves_existing_cache(self):
        expected = hashlib.sha256(self.map.read_bytes() + b'4.0room-v005-unmixed-248x454-lz4').hexdigest()[:16]
        env = room.environment(self.profile, self.manifest, True)
        self.assertTrue(env['GAHYEON_LOOKING_GLASS_CACHE_DIR'].endswith(expected))
        self.assertEqual(env['GAHYEON_LOOKING_GLASS_DEPTH_SCALE'], '0.45')

    def test_same_map_with_smaller_baseline_uses_new_cache(self):
        old = room.environment(self.profile, self.manifest, True)
        self.scene['captureDepthScale'] = 0.12
        self.save_scene()
        new = room.environment(self.profile, self.manifest, True)
        self.assertNotEqual(new['GAHYEON_LOOKING_GLASS_CACHE_DIR'], old['GAHYEON_LOOKING_GLASS_CACHE_DIR'])
        self.assertEqual(new['GAHYEON_LOOKING_GLASS_DEPTH_SCALE'], '0.12')
        self.assertEqual(new['GAHYEON_LOOKING_GLASS_RUNTIME_MAP'], old['GAHYEON_LOOKING_GLASS_RUNTIME_MAP'])
        self.assertEqual(new['GAHYEON_LOOKING_GLASS_VIEW_COUNT'], '66')

    def test_invalid_depth_fails_before_launch(self):
        for value in (0, -1, 1.01, float('nan'), float('inf'), 'invalid'):
            with self.subTest(value=value):
                self.scene['captureDepthScale'] = value
                self.save_scene()
                with self.assertRaises(ValueError):
                    room.environment(self.profile, self.manifest, True)
