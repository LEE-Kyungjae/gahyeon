import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_gahyeon_home_world_contract import parse_core, parse_unreal, verify


class HomeWorldContractTest(unittest.TestCase):
    def test_repository_contract_matches(self) -> None:
        root = Path(__file__).resolve().parents[1]
        verify(
            root / "src/main/java/com/gahyeonbot/core/behavior/GahyeonHomeWorld.java",
            root / "unreal/GahyeonStage/Source/GahyeonStage/Private/World/GahyeonPrototypeRoom.cpp")

    def test_axis_or_activity_drift_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            core = root / "Core.java"
            unreal = root / "Room.cpp"
            core.write_text(
                '"desk", point("desk", "workspace", 7, 0, -2, WorldActivity.WORK)',
                encoding="utf-8")
            unreal.write_text(
                'DeskPoint->SetRelativeLocation(FVector(700.0, 0.0, -200.0));\n'
                'DeskPoint->Configure(TEXT("desk"), TEXT("workspace"), {TEXT("sit")});',
                encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "position differs"):
                verify(core, unreal)

    def test_room_drift_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            core = root / "Core.java"
            unreal = root / "Room.cpp"
            core.write_text(
                '"desk", point("desk", "workspace", 7, 0, -2, WorldActivity.WORK)',
                encoding="utf-8")
            unreal.write_text(
                'DeskPoint->SetRelativeLocation(FVector(700.0, -200.0, 0.0));\n'
                'DeskPoint->Configure(TEXT("desk"), TEXT("bedroom"), {TEXT("work")});',
                encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "room differs"):
                verify(core, unreal)

    def test_unrelated_component_location_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            unreal = Path(temporary) / "Room.cpp"
            # "FillLight" and "DeskPoint" share the trailing "t".
            unreal.write_text(
                'FillLight->SetRelativeLocation(FVector(-180.0, 160.0, 260.0));\n'
                'DeskPoint->SetRelativeLocation(FVector(700.0, -200.0, 0.0));\n'
                'DeskPoint->Configure(TEXT("desk"), TEXT("workspace"), {TEXT("work")});',
                encoding="utf-8")
            self.assertEqual(
                parse_unreal(unreal)["desk"], ("workspace", (700.0, -200.0, 0.0), {"work"}))

    def test_parsers_reject_empty_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            empty = Path(temporary) / "empty"
            empty.write_text("", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "No Core"):
                parse_core(empty)
            with self.assertRaisesRegex(ValueError, "No Unreal"):
                parse_unreal(empty)


if __name__ == "__main__":
    unittest.main()
