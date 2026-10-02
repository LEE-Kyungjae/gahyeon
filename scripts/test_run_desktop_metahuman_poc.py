#!/usr/bin/env python3

import importlib.util
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("run_desktop_metahuman_poc.py")
SPEC = importlib.util.spec_from_file_location("desktop_metahuman_poc_runner", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class DesktopMetaHumanPocRunnerTest(unittest.TestCase):
    def test_command_uses_low_memory_desktop_profile(self):
        command = MODULE.build_launch_command(Path("/repo"), Path("/engine/UE_5.8"))
        self.assertIn("-ResX=1280", command)
        self.assertIn("-ResY=720", command)
        self.assertIn("-r.Streaming.PoolSize=384", command)
        self.assertIn("-r.HairStrands.Strands=0", command)
        self.assertNotIn("-game", command)

    def test_memory_failure_never_starts_editor(self):
        report = {"readyToOpenEditor": False, "actions": ["free memory"]}
        argv = [str(SCRIPT), "--workspace", "/repo"]
        with (
            mock.patch.object(MODULE.PREFLIGHT, "inspect_desktop_metahuman_poc", return_value=report),
            mock.patch.object(MODULE.subprocess, "Popen") as popen,
            mock.patch.object(MODULE.sys, "argv", argv),
        ):
            self.assertEqual(MODULE.main(), 2)
        popen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
