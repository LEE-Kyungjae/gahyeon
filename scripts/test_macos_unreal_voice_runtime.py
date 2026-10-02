import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MacOSUnrealVoiceRuntimeContractTest(unittest.TestCase):
    def test_launcher_enables_runtime_microphone_without_electron(self):
        launcher = (ROOT / "scripts/launch_canonical_macos_runtime.py").read_text()
        voice = (ROOT / "unreal/GahyeonStage/Source/GahyeonStage/Private/Voice/GahyeonVoiceInputComponent.cpp").read_text()
        project = (ROOT / "unreal/GahyeonDesktopMetaHumanPOC/GahyeonDesktopMetaHumanPOC.uproject").read_text()
        self.assertIn('"-GahyeonAutoStartMicrophone"', launcher)
        self.assertIn('TEXT("GahyeonAutoStartMicrophone")', voice)
        self.assertIn('"Name": "GahyeonVoiceRuntime"', project)
        self.assertIn('if "electron" not in value.get("retiredRuntimes", [])', launcher)
        self.assertNotIn("electron ", " ".join(launcher.split()).lower().split("return [", 1)[-1])


if __name__ == "__main__":
    unittest.main()
