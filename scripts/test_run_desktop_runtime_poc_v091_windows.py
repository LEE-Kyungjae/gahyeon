#!/usr/bin/env python3

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_desktop_runtime_poc_v091_windows.ps1"


class DesktopRuntimeV091WindowsContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SCRIPT.read_text(encoding="utf-8")

    def test_requires_native_windows_and_ue_58_package_gate(self):
        self.assertIn("[System.Environment]::OSVersion.Platform", self.source)
        self.assertIn("[System.PlatformID]::Win32NT", self.source)
        self.assertIn("if (-not $NativeWindows)", self.source)
        self.assertIn("run_unreal_engine_gate.ps1", self.source)
        self.assertIn("-Package", self.source)
        self.assertIn("GahyeonStage.exe", self.source)
        self.assertIn('$Executable = Join-Path $PackageRoot "GahyeonStage.exe"', self.source)
        self.assertIn('"GahyeonStage\\Binaries\\Win64\\GahyeonStage.exe"', self.source)
        self.assertNotIn("Get-ChildItem -LiteralPath (Join-Path $GateRoot", self.source)

    def test_uses_v091_map_and_fails_closed_on_missing_visual(self):
        self.assertIn("L_GahyeonDesktopRuntime_v091", self.source)
        self.assertIn("Gahyeon visual actor unavailable", self.source)
        self.assertIn("Fatal error:", self.source)

    def test_proves_window_capture_shutdown_and_restart(self):
        self.assertIn("nativeWindowObserved", self.source)
        self.assertIn("CopyFromScreen", self.source)
        self.assertIn('$BootstrapProcess = Start-Process', self.source)
        self.assertIn('[string]::Equals($_.Path, $RuntimeExecutable', self.source)
        self.assertIn('$WindowProcess.MainWindowHandle', self.source)
        self.assertIn('$Result["logSha256"] = (Get-FileHash', self.source)
        self.assertLess(
            self.source.index("$WindowProcess.WaitForExit(15000)"),
            self.source.index('$Result["logSha256"] = (Get-FileHash'),
        )
        self.assertIn('Invoke-GahyeonVisualRun -Name "first-launch"', self.source)
        self.assertIn('Invoke-GahyeonVisualRun -Name "restart"', self.source)
        self.assertIn("CloseMainWindow", self.source)

    def test_can_run_long_realtime_acceptance(self):
        self.assertIn("RunRealtimeAcceptance", self.source)
        self.assertIn("run_desktop_realtime_acceptance.ps1", self.source)
        self.assertIn("-RequirePassed", self.source)

    def test_manifest_write_is_windows_powershell_51_compatible(self):
        self.assertIn("System.Text.UTF8Encoding($false)", self.source)
        self.assertIn("[System.IO.File]::WriteAllText", self.source)
        self.assertNotIn("-Encoding utf8NoBOM", self.source)


if __name__ == "__main__":
    unittest.main()
