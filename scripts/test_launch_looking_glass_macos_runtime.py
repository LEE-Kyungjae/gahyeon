#!/usr/bin/env python3

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class LookingGlassMacosRuntimeTest(unittest.TestCase):
    def test_launcher_enables_true_unreal_multiview_capture(self):
        launcher = (ROOT / "scripts/launch_looking_glass_macos_runtime.py").read_text()
        runtime = (ROOT / "unreal/GahyeonDesktopMetaHumanPOC/Source/"
                   "GahyeonDesktopMetaHumanPOC/Private/GahyeonDesktopMetaHumanPOC.cpp").read_text()
        iosurface_bridge = (ROOT / "unreal/GahyeonDesktopMetaHumanPOC/Source/"
                            "GahyeonDesktopMetaHumanPOC/Private/MacIOSurfaceBridge.mm").read_text()
        encoder = (ROOT / "native/macos/GahyeonLookingGlassBridge/frame_encoder.mm").read_text()
        self.assertIn('runtime_environment["GAHYEON_LOOKING_GLASS_QUILT"] = "1"', launcher)
        self.assertIn('runtime_environment["GAHYEON_LOOKING_GLASS_NO_OVERLAY"] = "1"', launcher)
        self.assertIn("read_display_profile()", launcher)
        self.assertIn('runtime_environment["GAHYEON_LOOKING_GLASS_VIEW_CONE"]', launcher)
        self.assertIn('runtime_environment["GAHYEON_LOOKING_GLASS_VIEW_COUNT"]', launcher)
        self.assertIn('runtime_environment["GAHYEON_LOOKING_GLASS_RUNTIME_MAP"]', launcher)
        self.assertIn('stream_environment["GAHYEON_LOOKING_GLASS_ANIMATED_QA"] = "1"', launcher)
        self.assertIn('runtime_environment["GAHYEON_LOOKING_GLASS_ANIMATED_QA"] = "1"', launcher)
        self.assertIn("time.sleep(2.0)", launcher)
        self.assertIn("LookingGlassViewCount = 66", runtime)
        self.assertIn("LookingGlassDepthScale = 0.45f", runtime)
        self.assertIn("Mesh->bPauseAnims = true", runtime)
        self.assertNotIn("SetGamePaused(World, true)", runtime)
        self.assertIn('GetSocketLocation(TEXT("head"))', runtime)
        self.assertIn("const float ViewT = 1.0f", runtime)
        self.assertIn("GetHorizontalProjectionOffset", runtime)
        self.assertIn("SensorHorizontalOffset", runtime)
        self.assertIn("PrepareLookingGlassView", runtime)
        self.assertIn("ConfigureGahyeonMacIOSurfaceQuilt(CurrentViewIndex, 1)", runtime)
        self.assertIn("bGPUWarmupPending", runtime)
        self.assertIn("LookingGlassAnimationFrameCount = 12", runtime)
        self.assertIn("SetPosition(PoseSeconds, false)", runtime)
        self.assertIn("SingleNode->GetLength()", runtime)
        self.assertIn("MarkRenderDynamicDataDirty()", runtime)
        self.assertIn("duration=%.3f head=%s", runtime)
        self.assertIn("Header->Sequence != Header->ConsumerSequence", iosurface_bridge)
        self.assertIn("ViewGeneration == PublishedViewGeneration.Load()", iosurface_bridge)
        self.assertIn("++RequestedViewGeneration", iosurface_bridge)
        self.assertIn("header->viewIndex", encoder)
        self.assertIn("viewIndex + 1 == viewCount", encoder)
        self.assertIn("consumerSequence", encoder)
        self.assertIn("O_RDWR", encoder)
        self.assertIn("PROT_READ | PROT_WRITE", encoder)
        self.assertIn("GAHYEON_LKG_QUILT_REJECTED", encoder)
        self.assertIn("GAHYEON_LKG_ACK_WAIT", encoder)
        self.assertIn("quiltCoverage", encoder)

    def test_one_stop_launcher_uses_canonical_unreal_and_native_bridge(self):
        source = (ROOT / "scripts/launch_looking_glass_macos_runtime.py").read_text()
        self.assertIn("launch_canonical_macos_runtime.py", source)
        self.assertIn("setup_looking_glass_macos.py", source)
        self.assertIn("GahyeonLookingGlassFrameEncoder", source)
        self.assertIn('stream = subprocess.Popen([str(ENCODER)]', source)
        self.assertIn("GAHYEON_LOOKING_GLASS_ANIMATED_QA", source)
        self.assertNotIn("desktop/package", source)
        self.assertNotIn("electron", source.lower())

    def test_stream_uses_native_bridge_metal_interop(self):
        source = (ROOT / "native/macos/GahyeonLookingGlassBridge/frame_encoder.mm").read_text()
        self.assertIn("instance_window_metal", source)
        self.assertIn("draw_interop_quilt_texture_metal", source)
        self.assertIn("create_metal_texture_with_iosurface", source)
        self.assertIn("set_window_polling(window, true)", source)
        self.assertIn("PumpAppEvents", source)
        self.assertIn("NSOpenGLContext", source)
        self.assertIn("makeCurrentContext", source)
        self.assertIn("gl_bootstrap=1", source)
        self.assertIn("IOSurfaceLookup", source)
        self.assertIn("GAHYEON_LKG_GPU_QUILT", source)
        self.assertIn("blendViews", source)
        self.assertIn("GAHYEON_LKG_VIEW_BLEND center=0.88 adjacent=0.06", source)
        self.assertIn("GAHYEON_LKG_IDLE_FRAME_READY", source)
        self.assertIn("GAHYEON_LKG_IDLE_LOOP_READY", source)
        self.assertIn("GAHYEON_LKG_IDLE_PLAYBACK", source)
        self.assertIn("draw_interop_quilt_texture_metal(window, blendedRaw", source)
        self.assertIn("AnimatedFrameCount = 12", source)
        self.assertIn("GAHYEON_LKG_FLAT_IMAGE_READY", source)
        self.assertIn("GAHYEON_LKG_GPU_QUILT", source)
        self.assertIn("FIRST_LOOKING_GLASS_DEVICE", source)
        self.assertIn("GAHYEON_LKG_METAL_READY", source)


if __name__ == "__main__":
    unittest.main()
