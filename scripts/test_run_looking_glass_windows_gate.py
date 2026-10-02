#!/usr/bin/env python3

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_looking_glass_windows_gate.ps1"


class LookingGlassWindowsGateContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SCRIPT.read_text(encoding="utf-8")

    def test_targets_ue58_win64_profile_without_uba(self):
        self.assertIn("GahyeonStageLookingGlass.uproject", self.source)
        self.assertIn("MinorVersion -ne 8", self.source)
        self.assertIn("GahyeonStageEditor Win64 Development", self.source)
        self.assertIn("-NoUBA", self.source)

    def test_manifest_program_uses_stdin_on_windows_powershell_51(self):
        self.assertIn("$ManifestScript | & $Python - $EvidenceRoot", self.source)
        self.assertNotIn("& $Python -c $ManifestScript", self.source)


if __name__ == "__main__":
    unittest.main()
