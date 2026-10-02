import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).with_name("run_land_desktop_airi_poc.py")


def load_module():
    spec = importlib.util.spec_from_file_location("run_land_desktop_airi_poc", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class LandDesktopAiriPocTest(unittest.TestCase):
    def test_absent_windows_process_is_an_idempotent_success(self):
        module = load_module()
        calls = []

        def fake_run(command, **_kwargs):
            calls.append(command)
            if command == ["ssh", "land", "hostname", "-I"]:
                return "172.23.1.2"
            return ""

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            (output / "Gahyeon.exe").touch()
            with mock.patch.object(module, "OUTPUT", output), mock.patch.object(module, "run", fake_run), mock.patch.dict(
                os.environ, {"GAHYEON_CLIENT_TOKEN": "test-token-long-enough"}
            ), mock.patch("sys.argv", [str(SCRIPT), "--skip-build"]):
                module.main()

        stop_command = calls[0][-1]
        self.assertIn("[Console]::OutputEncoding = [System.Text.Encoding]::UTF8", stop_command)
        self.assertIn("\\$Processes = @(Get-Process Gahyeon", stop_command)
        self.assertIn("if (\\$Processes.Count -gt 0)", stop_command)
        self.assertTrue(stop_command.endswith("exit 0\""))


if __name__ == "__main__":
    unittest.main()
