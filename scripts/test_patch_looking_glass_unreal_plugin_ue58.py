#!/usr/bin/env python3

import tempfile
import unittest
from pathlib import Path

from patch_looking_glass_unreal_plugin_ue58 import PATCH_ID, apply_patch


class LookingGlassUe58PatchTest(unittest.TestCase):
    def test_patch_is_strict_and_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            plugin = Path(temporary)
            runtime = plugin / "Source/LookingGlassRuntime"
            fixtures = {
                "Private/Render/LookingGlassRendering.cpp": '#include "CommonRenderResources.h"\n',
                "Private/Render/LookingGlassViewportClient.cpp": (
                    '#include "ScreenRendering.h"\n'
                    "bool FLookingGlassViewportClient::InputTouch(FViewport* InViewport, const FInputDeviceId DeviceId, uint32 Handle, ETouchType::Type Type, const FVector2D& TouchLocation, float Force, uint32 TouchpadIndex, const uint64 Timestamp)\n{\n"
                    "\t\tbResult = GEngine->GameViewport->ViewportConsole->InputTouch(DeviceId, Handle, Type, TouchLocation, Force, TouchpadIndex, Timestamp);\n"
                    "\t\t\tbResult = TargetPlayer->PlayerController->InputTouch(DeviceId, Handle, Type, TouchLocation, Force, TouchpadIndex, Timestamp);\n"
                ),
                "Public/Game/LookingGlassSceneCaptureComponent2D.h": "\tvirtual void PostInterpChange(FProperty* PropertyThatChanged) override;\n",
                "Private/Game/LookingGlassSceneCaptureComponent2D.cpp": (
                    "void ULookingGlassSceneCaptureComponent2D::PostInterpChange(FProperty* PropertyThatChanged)\n{\n"
                    "\t}\n}\n\n// This function is called when \"Size\" property is changed"
                ),
                "Public/Render/LookingGlassViewportClient.h": "\tvirtual bool InputTouch(FViewport* Viewport, const FInputDeviceId DeviceId, uint32 Handle, ETouchType::Type Type, const FVector2D& TouchLocation, float Force, uint32 TouchpadIndex, const uint64 Timestamp) override;\n",
            }
            for relative, content in fixtures.items():
                path = runtime / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)

            first = apply_patch(plugin)
            second = apply_patch(plugin)
            self.assertEqual("patched", first["status"])
            self.assertEqual("already-patched", second["status"])
            self.assertEqual(PATCH_ID, second["patchId"])
            self.assertTrue((plugin / ".gahyeon-ue58-compat.json").is_file())
            viewport = (runtime / "Public/Render/LookingGlassViewportClient.h").read_text()
            self.assertIn("const FTouchId TouchId", viewport)
            self.assertIn("ENGINE_MINOR_VERSION >= 8", viewport)


if __name__ == "__main__":
    unittest.main()
