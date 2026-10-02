import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MacOSOverlayCharacterControlsTest(unittest.TestCase):
    def test_native_right_drag_rotation_and_reset_are_wired_to_unreal(self):
        swift = (ROOT / "native/macos/GahyeonUnrealOverlay/main.swift").read_text(encoding="utf-8")
        runtime = (ROOT / "unreal/GahyeonDesktopMetaHumanPOC/Source/GahyeonDesktopMetaHumanPOC/Private/GahyeonDesktopMetaHumanPOC.cpp").read_text(encoding="utf-8")
        launcher = (ROOT / "scripts/launch_canonical_macos_runtime.py").read_text(encoding="utf-8")

        self.assertIn("rightMouseDragged", swift)
        self.assertIn("acceptsFirstMouse", swift)
        self.assertIn("InteractiveOverlayWindow", swift)
        self.assertIn("onHorizontalRotationDelta", swift)
        self.assertIn("characterYaw + horizontalDelta * 0.35", swift)
        self.assertIn("정위치 (위치·크기·회전)", swift)
        self.assertIn("controlWriter.publish(yaw: 0, reset: true)", swift)
        self.assertIn("gahyeon_overlay_control_v001", runtime)
        self.assertIn("FMath::Clamp(Control->YawDegrees, -75.0f, 75.0f)", runtime)
        self.assertIn("Rotation.Yaw = *InitialYaw + Yaw", runtime)
        self.assertIn("OVERLAY_CONTROL_MEMORY_NAME", launcher)
        self.assertIn("terminate_existing_runtime(command, overlay_binary)", launcher)


if __name__ == "__main__":
    unittest.main()
