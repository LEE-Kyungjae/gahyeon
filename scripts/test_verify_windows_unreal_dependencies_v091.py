import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("verify_windows_unreal_dependencies_v091.py")
SPEC = importlib.util.spec_from_file_location("windows_dependencies_v091", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class WindowsDependenciesV091Test(unittest.TestCase):
    def fixture(self) -> tuple[tempfile.TemporaryDirectory, Path, Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        engine = root / "UE_5.8"
        workspace = root / "repo"
        for relative in (
            "Engine/Build/BatchFiles/RunUAT.bat",
            "Engine/Binaries/Win64/UnrealEditor.exe",
            "Engine/Plugins/MetaHuman/MetaHumanSDK/Content/TemplateAssets/SM_MH_Head.uasset",
        ):
            path = engine / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
        (engine / "Engine/Plugins/MetaHuman/MetaHumanCharacter/Content").mkdir(parents=True)
        for role, names in MODULE.ENGINE_PLUGIN_GROUPS.items():
            path = engine / "Engine/Plugins/Test" / role / f"{names[0]}.uplugin"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}", encoding="utf-8")
        project = workspace / "unreal/GahyeonStage/GahyeonStage.uproject"
        project.parent.mkdir(parents=True, exist_ok=True)
        project.write_text(
            json.dumps({
                "EngineAssociation": "5.8",
                "Plugins": [
                    {"Name": name, "Enabled": True}
                    for name in sorted(MODULE.PROJECT_PLUGINS)
                ],
            }),
            encoding="utf-8",
        )
        for relative in (
            "unreal/GahyeonStage/Content/Gahyeon/CharacterPipeline/v088/AssembledMedium/Skotukeda_WardrobeGroomQA_v088/BP_Skotukeda_WardrobeGroomQA_v088.uasset",
            "unreal/GahyeonStage/Content/Gahyeon/DesktopRuntime/v091/L_GahyeonDesktopRuntime_v091.umap",
            "unreal/GahyeonStage/Content/Fab/MetaHuman/Skotukeda.uasset",
        ):
            path = workspace / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
        return temporary, engine, workspace

    def test_ready_fixture_passes(self) -> None:
        temporary, engine, workspace = self.fixture()
        self.addCleanup(temporary.cleanup)
        report = MODULE.inspect(engine, workspace)
        self.assertTrue(report["readyForWindowsPackage"])
        self.assertEqual(report["status"], "ready")

    def test_missing_core_data_fails_closed(self) -> None:
        temporary, engine, workspace = self.fixture()
        self.addCleanup(temporary.cleanup)
        (engine / "Engine/Plugins/MetaHuman/MetaHumanSDK/Content/TemplateAssets/SM_MH_Head.uasset").unlink()
        report = MODULE.inspect(engine, workspace)
        self.assertFalse(report["readyForWindowsPackage"])
        self.assertIn("metaHumanHeadTemplate", report["missingMarkers"])

    def test_missing_project_plugin_is_reported(self) -> None:
        temporary, engine, workspace = self.fixture()
        self.addCleanup(temporary.cleanup)
        project = workspace / "unreal/GahyeonStage/GahyeonStage.uproject"
        descriptor = json.loads(project.read_text(encoding="utf-8"))
        descriptor["Plugins"] = [
            item for item in descriptor["Plugins"] if item["Name"] != "LiveLink"
        ]
        project.write_text(json.dumps(descriptor), encoding="utf-8")
        report = MODULE.inspect(engine, workspace)
        self.assertIn("LiveLink", report["missingProjectPlugins"])


if __name__ == "__main__":
    unittest.main()
