#!/usr/bin/env python3
import os
import unittest
from unittest.mock import patch
from launch_canonical_macos_runtime import build_command, load_manifest

class OffscreenRuntimeTest(unittest.TestCase):
    def test_default_hides_renderer_without_disabling_cpu_frames(self):
        with patch.dict(os.environ, {}, clear=True):
            command = build_command(load_manifest())
        self.assertIn('-RenderOffscreen', command)
        self.assertIn('-GahyeonCPUAlphaFallback', command)
        self.assertNotIn('-GahyeonAutoStartMicrophone', command)

    def test_diagnostic_window_requires_explicit_override(self):
        with patch.dict(os.environ, {'GAHYEON_RENDER_OFFSCREEN': '0'}, clear=True):
            self.assertNotIn('-RenderOffscreen', build_command(load_manifest()))

if __name__ == '__main__':
    unittest.main()
