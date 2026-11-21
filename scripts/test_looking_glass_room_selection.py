"""Room selection must change both map and cache without changing default launch."""
import json
import unittest
import test_looking_glass_room_clarity as baseline_tests
import launch_gahyeon_looking_glass_room_v011 as room


class RoomSelectionTests(baseline_tests.RoomEnvironmentTests):
    def test_explicit_room_uses_its_own_map_and_cache(self):
        baseline = room.environment(self.profile, self.manifest, True)
        candidate = dict(self.scene, map='/Game/RoomDetail')
        (self.root/'config/detail.json').write_text(json.dumps(candidate))
        (self.map.parent/'RoomDetail.umap').write_bytes(b'new detailed room')
        env = room.environment(self.profile, self.manifest, True, 'detail.json')
        self.assertEqual(env['GAHYEON_LOOKING_GLASS_RUNTIME_MAP'], '/Game/RoomDetail')
        self.assertNotEqual(env['GAHYEON_LOOKING_GLASS_CACHE_DIR'], baseline['GAHYEON_LOOKING_GLASS_CACHE_DIR'])
        self.assertEqual(room.environment(self.profile, self.manifest, True), baseline)

    def test_room_path_cannot_escape_config_directory(self):
        with self.assertRaises(ValueError):
            room.environment(self.profile, self.manifest, True, '../detail.json')


if __name__ == '__main__':
    unittest.main()
