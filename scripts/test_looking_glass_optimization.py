"""Runtime profile isolation and consumer startup ordering regressions."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import launch_canonical_macos_runtime as canonical
import launch_looking_glass_macos_runtime as looking_glass


class LookingGlassOptimizationTest(unittest.TestCase):
    def test_tile_profile_preserves_aspect_and_desktop_defaults(self):
        for quilt, profile, dimensions in (
            ("1", "tile-v001", (800, 629)),
            ("1", "baseline", (1600, 1258)),
            ("0", "tile-v001", (1600, 1258)),
        ):
            with self.subTest(quilt=quilt, profile=profile), patch.dict(os.environ, {
                "GAHYEON_LOOKING_GLASS_QUILT": quilt,
                "GAHYEON_LOOKING_GLASS_RENDER_PROFILE": profile,
            }, clear=True):
                command = canonical.build_command(canonical.load_manifest())
                width, height = dimensions
                self.assertIn(f"-ResX={width}", command)
                self.assertIn(f"-ResY={height}", command)
                self.assertEqual(width * 1258, height * 1600)

    def test_invalid_quilt_profile_fails_closed(self):
        with patch.dict(os.environ, {
            "GAHYEON_LOOKING_GLASS_QUILT": "1",
            "GAHYEON_LOOKING_GLASS_RENDER_PROFILE": "typo",
        }, clear=True), self.assertRaises(RuntimeError):
            canonical.build_command(canonical.load_manifest())

    def test_ready_signal_follows_stale_memory_cleanup_and_spawn(self):
        with tempfile.TemporaryDirectory() as directory:
            ready = Path(directory) / "ready"
            events = []
            process = Mock(pid=123, wait=Mock(return_value=0), poll=Mock(return_value=0))

            def spawn(*args, **kwargs):
                self.assertEqual(events, ["cleanup"])
                self.assertFalse(ready.exists())
                events.append("spawn")
                return process

            def after_spawn(seconds):
                self.assertEqual(ready.read_text(), "123")
                self.assertEqual(events, ["cleanup", "spawn"])

            with patch.dict(os.environ, {
                "GAHYEON_RUNTIME_READY_FILE": str(ready),
                "GAHYEON_LOOKING_GLASS_NO_OVERLAY": "1",
            }, clear=True), patch.object(canonical, "build_command", return_value=["runtime"]), \
                patch.object(canonical, "load_manifest", return_value={}), \
                patch.object(canonical, "build_overlay", return_value=Path("overlay")), \
                patch.object(canonical, "frontmost_application_name", return_value=""), \
                patch.object(canonical, "reactivate_application"), \
                patch.object(canonical, "terminate_existing_runtime"), \
                patch.object(canonical, "unlink_stale_shared_memory", side_effect=lambda: events.append("cleanup")), \
                patch.object(canonical.subprocess, "Popen", side_effect=spawn), \
                patch.object(canonical.time, "sleep", side_effect=after_spawn):
                self.assertEqual(canonical.main(), 0)

    def test_consumer_waits_for_delayed_runtime_readiness(self):
        runtime = Mock(returncode=0, poll=Mock(return_value=None))
        stream = Mock(returncode=0, poll=Mock(return_value=0))
        state = {"ready": None, "waited": False}

        def spawn(command, **kwargs):
            if "GAHYEON_RUNTIME_READY_FILE" in kwargs["env"]:
                state["ready"] = Path(kwargs["env"]["GAHYEON_RUNTIME_READY_FILE"])
                return runtime
            self.assertTrue(state["waited"], "consumer started before producer readiness")
            return stream

        def delayed_start(seconds):
            if seconds == 0.05:
                state["waited"] = True
                state["ready"].write_text("123")

        with patch.dict(os.environ, {}, clear=True), \
            patch.object(looking_glass.subprocess, "run"), \
            patch.object(looking_glass.subprocess, "Popen", side_effect=spawn), \
            patch.object(looking_glass, "build_encoder"), \
            patch.object(looking_glass, "read_display_profile", return_value=(54.0, 66)), \
            patch.object(looking_glass.time, "sleep", side_effect=delayed_start), \
            patch.object(looking_glass.signal, "signal"), \
            patch.object(looking_glass, "terminate"):
            self.assertEqual(looking_glass.main(), 0)


if __name__ == "__main__":
    unittest.main()
