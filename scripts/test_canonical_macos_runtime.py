#!/usr/bin/env python3

import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


class CanonicalMacosRuntimeTest(unittest.TestCase):
    def test_looking_glass_mode_uses_bounded_memory_quality(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        from launch_canonical_macos_runtime import build_command, load_manifest

        with patch.dict("os.environ", {"GAHYEON_LOOKING_GLASS_QUILT": "1"}, clear=True):
            command = build_command(load_manifest())
        commands = next(item for item in command if item.startswith("-ExecCmds="))
        self.assertIn("r.TextureStreaming 1", commands)
        self.assertIn("r.Streaming.PoolSize 512", commands)
        self.assertIn("r.ScreenPercentage 125", commands)
        self.assertIn("r.MaxAnisotropy 16", commands)
        self.assertIn("r.MipMapLODBias -1", commands)
        self.assertIn("r.Tonemapper.Sharpen 0.8", commands)
        self.assertIn("r.SkeletalMeshLODBias 0", commands)
        self.assertNotIn("r.TextureStreaming 0", commands)

    def test_looking_glass_mode_is_explicitly_opt_in(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        from launch_canonical_macos_runtime import build_command, load_manifest

        with patch.dict("os.environ", {}, clear=True):
            self.assertNotIn("-GahyeonLookingGlassQuilt", build_command(load_manifest()))
            self.assertIn("-GahyeonCPUAlphaFallback", build_command(load_manifest()))
        with patch.dict("os.environ", {"GAHYEON_LOOKING_GLASS_QUILT": "1"}, clear=True):
            self.assertIn("-GahyeonLookingGlassQuilt", build_command(load_manifest()))
            self.assertNotIn("-GahyeonCPUAlphaFallback", build_command(load_manifest()))

    def test_manifest_selects_unreal_and_retires_electron(self):
        value = json.loads((ROOT / "config/canonical-character-runtime.json").read_text())
        self.assertEqual("unreal", value["runtime"])
        self.assertIn("electron", value["retiredRuntimes"])
        self.assertEqual("ready", value["status"])
        self.assertEqual(
            "/Game/Gahyeon/Character2/Diana/v398/Runtime/L_DianaMacRuntimeOriginalMaterialSafeFrame_v398",
            value["macos"]["runtimeMap"],
        )
        self.assertEqual("unreal-macos-direct-alpha-shared-memory", value["macos"]["launchMode"])

    def test_electron_service_commands_fail_closed(self):
        package = json.loads((ROOT / "desktop/package.json").read_text())
        for name in ("dev", "start", "package", "dist"):
            self.assertEqual("node tools/retired-runtime-check.mjs", package["scripts"][name])
        result = subprocess.run(
            ["node", "tools/retired-runtime-check.mjs"], cwd=ROOT / "desktop",
            text=True, capture_output=True, check=False,
        )
        self.assertEqual(2, result.returncode)
        self.assertIn("RETIRED_RUNTIME", result.stderr)

    def test_canonical_launcher_selects_promoted_unreal_map(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        from launch_canonical_macos_runtime import build_command, load_manifest

        command = build_command(load_manifest())
        self.assertIn("-game", command)
        self.assertIn("-ForceRes", command)
        self.assertIn("-ResX=1600", command)
        self.assertIn("-ResY=1258", command)
        self.assertTrue(any("r.MotionBlurQuality 0" in item for item in command))
        self.assertTrue(any("r.ScreenPercentage 100" in item for item in command))
        self.assertTrue(any("r.Tonemapper.Sharpen 0.0" in item for item in command))
        self.assertTrue(any("r.AntiAliasingMethod 1" in item for item in command))
        self.assertTrue(any("r.ExposureOffset 0.5" in item for item in command))
        self.assertTrue(any("r.TextureStreaming 0" in item for item in command))
        self.assertIn(
            "/Game/Gahyeon/Character2/Diana/v398/Runtime/L_DianaMacRuntimeOriginalMaterialSafeFrame_v398",
            command,
        )

    def test_native_overlay_keeps_full_body_drag_and_utility_controls(self):
        source = (ROOT / "native/macos/GahyeonUnrealOverlay/main.swift").read_text()
        self.assertIn("value.isMovableByWindowBackground = true", source)
        self.assertIn("final class DragImageView", source)
        self.assertIn("window?.ignoresMouseEvents = clickThrough", source)
        self.assertIn("installMenu()", source)
        self.assertIn("createPanel()", source)
        self.assertIn("imageView.frame = surface.bounds.insetBy", source)
        self.assertIn("screen.visibleFrame.height * 0.65, 640", source)
        self.assertIn("captureAspect: CGFloat = 1600.0 / 1258.0", source)
        self.assertIn("(height - verticalContentInset * 2) * captureAspect", source)
        self.assertIn("value.constrainFrameRect(frame, to: screen)", source)
        self.assertIn("SharedRGBAReader", source)
        self.assertIn("/gahyeon_rgba_v003", source)
        self.assertIn("final class DesktopCoreClient", source)
        self.assertIn("final class NativeSpeechInput", source)
        self.assertIn("LiquidGlassHighlightView", source)
        self.assertIn('islandButton("person.crop.circle"', source)
        self.assertIn("@objc private func toggleMicrophone()", source)
        self.assertIn("@objc private func toggleSound()", source)
        self.assertIn("@objc private func toggleChat()", source)
        self.assertIn("@objc private func sendChat()", source)
        self.assertIn("@objc private func changeCharacterModel()", source)
        self.assertIn("let grid = NSGridView(views:", source)
        self.assertIn("for row in 0..<3", source)
        self.assertIn("effect.material = .underWindowBackground", source)
        self.assertNotIn("effect.alphaValue", source)
        self.assertIn("window.frame.maxX - panel.frame.width - inset", source)
        self.assertIn("window.frame.minY + inset + 42", source)
        self.assertNotIn('islandButton("chevron.down", #selector(toggleControls)', source)
        self.assertIn("/gahyeon/desktop/conversations/", source)
        self.assertIn("/gahyeon/desktop/speech/status", source)
        self.assertNotIn("ScreenCaptureKit", source)
        self.assertNotIn("CIColorCube", source)


if __name__ == "__main__":
    unittest.main()
