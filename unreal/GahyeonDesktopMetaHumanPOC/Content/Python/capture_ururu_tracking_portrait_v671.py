"""Capture a readable UE portrait before another Ururu conform attempt."""

import hashlib
import json
from pathlib import Path
import time

import unreal


MESH = (
    "/Game/LivingCharacterPOC/v585/Characters/UruruCentimeterNormalized/"
    "Ururu_CentimeterNormalized_v584"
)
MAP = "/Game/LivingCharacterPOC/v671/Preview/L_UruruTrackingPortrait_v671"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/"
    "living-character-poc-v671-ururu-tracking-portrait"
)
_driver_v671 = None


class UruruTrackingPortraitV671:
    def __init__(self):
        if OUTPUT.exists() or unreal.EditorAssetLibrary.does_asset_exist(MAP):
            raise RuntimeError("refusing to overwrite immutable v671 evidence")
        mesh = unreal.load_asset(MESH)
        if mesh is None or mesh.get_class().get_name() != "SkeletalMesh":
            raise RuntimeError("validated Ururu v585 mesh is unavailable")
        OUTPUT.mkdir(parents=True, exist_ok=False)
        if not unreal.EditorLevelLibrary.new_level(MAP):
            raise RuntimeError("failed to create v671 portrait map")
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        character = actors.spawn_actor_from_class(
            unreal.SkeletalMeshActor, unreal.Vector(), unreal.Rotator()
        )
        character.set_actor_label("UruruTrackingPreview_v671")
        character.get_component_by_class(unreal.SkeletalMeshComponent).set_editor_property(
            "skeletal_mesh_asset", mesh
        )
        self.origin, self.extent = character.get_actor_bounds(False, True)
        height = self.extent.z * 2.0
        if not 130.0 <= height <= 190.0:
            raise RuntimeError(f"implausible Ururu height: {height}")
        self.target = unreal.Vector(
            self.origin.x,
            self.origin.y,
            self.origin.z + self.extent.z * 0.72,
        )
        camera_location = self.target + unreal.Vector(0.0, 155.0, 0.0)
        self.camera = actors.spawn_actor_from_class(
            unreal.CineCameraActor,
            camera_location,
            unreal.MathLibrary.find_look_at_rotation(camera_location, self.target),
        )
        component = self.camera.get_cine_camera_component()
        component.set_editor_property("current_focal_length", 55.0)
        component.set_editor_property("current_aperture", 8.0)
        focus = component.get_editor_property("focus_settings")
        focus.set_editor_property("focus_method", unreal.CameraFocusMethod.DISABLE)
        component.set_editor_property("focus_settings", focus)
        for offset, intensity in (
            (unreal.Vector(-85.0, 110.0, 45.0), 2600.0),
            (unreal.Vector(85.0, 100.0, 20.0), 1500.0),
            (unreal.Vector(0.0, -90.0, 55.0), 2000.0),
        ):
            location = self.target + offset
            light = actors.spawn_actor_from_class(
                unreal.RectLight,
                location,
                unreal.MathLibrary.find_look_at_rotation(location, self.target),
            )
            light_component = light.get_component_by_class(unreal.RectLightComponent)
            light_component.set_editor_property("intensity", intensity)
            light_component.set_editor_property("source_width", 90.0)
            light_component.set_editor_property("source_height", 90.0)
        sky = actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector())
        sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property(
            "intensity", 0.7
        )
        post = actors.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector())
        post.set_editor_property("unbound", True)
        settings = post.get_editor_property("settings")
        settings.set_editor_property("override_auto_exposure_method", True)
        settings.set_editor_property(
            "auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL
        )
        settings.set_editor_property("override_auto_exposure_bias", True)
        settings.set_editor_property("auto_exposure_bias", 0.0)
        settings.set_editor_property("override_motion_blur_amount", True)
        settings.set_editor_property("motion_blur_amount", 0.0)
        post.set_editor_property("settings", settings)
        if not unreal.EditorLevelLibrary.save_current_level():
            raise RuntimeError("failed to save v671 portrait map")
        self.output = OUTPUT / "ururu-front.png"
        self.warmup = 240
        self.started = None
        unreal.EditorPythonScripting.set_keep_python_script_alive(True)
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def tick(self, _delta):
        if self.warmup:
            self.warmup -= 1
            return
        if self.started is None:
            self.started = time.monotonic()
            unreal.AutomationLibrary.take_high_res_screenshot(
                1200, 1200, str(self.output), self.camera
            )
            return
        if self.output.is_file() and self.output.stat().st_size > 1024:
            report = {
                "schemaVersion": 1,
                "iteration": "v671",
                "state": "captured-pre-conform-tracking-portrait",
                "mesh": MESH,
                "map": MAP,
                "bounds": {
                    "origin": [self.origin.x, self.origin.y, self.origin.z],
                    "extent": [self.extent.x, self.extent.y, self.extent.z],
                },
                "faceTarget": [self.target.x, self.target.y, self.target.z],
                "file": str(self.output),
                "sha256": hashlib.sha256(self.output.read_bytes()).hexdigest(),
                "visualValidationPending": True,
                "automaticApproval": False,
            }
            (OUTPUT / "report.json").write_text(
                json.dumps(report, indent=2) + "\n", encoding="utf-8"
            )
            unreal.unregister_slate_post_tick_callback(self.handle)
            unreal.EditorPythonScripting.set_keep_python_script_alive(False)
            unreal.SystemLibrary.quit_editor()
        elif time.monotonic() - self.started > 180:
            raise RuntimeError("v671 portrait capture timed out")


def capture_ururu_tracking_portrait_v671():
    global _driver_v671
    _driver_v671 = UruruTrackingPortraitV671()


capture_ururu_tracking_portrait_v671()
