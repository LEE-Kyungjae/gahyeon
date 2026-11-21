import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import launch_gahyeon_looking_glass_room_v011 as room


class RoomEnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.patch = patch.object(room, 'ROOT', self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.profile = dict(viewCone=54, viewCount=66, displayId=1)
        self.manifest = dict(status='ready', macos=dict(characterModelId='gahyeon',
            animationProfile='idle.json', runtimeMap='/Game/Base'))
        (self.root/'idle.json').write_text(json.dumps({'animations':[{'role':'idle','seconds':8}]}))
        self.scene = dict(character='/Game/Gahyeon_Land_Idle_v001.Gahyeon_Land_Idle_v001',
            sampleSeconds=4, cachedFrames=120, map='/Game/Room')
        (self.root/'config').mkdir()
        self.map = self.root/'unreal/GahyeonDesktopMetaHumanPOC/Content/Room.umap'
        self.map.parent.mkdir(parents=True)
        self.map.write_bytes(b'first room')
        self.save_scene()

    def save_scene(self):
        (self.root/'config/looking-glass-room-v011.json').write_text(json.dumps(self.scene))

    def test_changed_map_cannot_restore_old_quilt_cache(self):
        first = room.environment(self.profile, self.manifest, True)
        self.map.write_bytes(b'changed room depth')
        second = room.environment(self.profile, self.manifest, True)
        self.assertNotEqual(first['GAHYEON_LOOKING_GLASS_CACHE_DIR'], second['GAHYEON_LOOKING_GLASS_CACHE_DIR'])

    def test_short_animation_uses_same_capture_and_playback_duration(self):
        (self.root/'idle.json').write_text(json.dumps({'animations':[{'role':'idle','seconds':2}]}))
        env = room.environment(self.profile, self.manifest, True)
        self.assertEqual(float(env['GAHYEON_LOOKING_GLASS_SAMPLE_SECONDS']), 2)
        self.assertEqual(env['GAHYEON_LOOKING_GLASS_SAMPLE_SECONDS'], env['GAHYEON_LOOKING_GLASS_CLIP_SECONDS'])

    def test_wrong_character_fails_before_launch(self):
        self.scene['character'] = '/Game/Other.Other'
        self.save_scene()
        with self.assertRaisesRegex(RuntimeError, 'identity mismatch'):
            room.environment(self.profile, self.manifest, True)


if __name__ == '__main__':
    unittest.main()
