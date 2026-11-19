"""Reusable fixed-camera UE capture for an imported character bind pose."""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import time

import unreal


@dataclass(frozen=True)
class LivingCharacterBindQACaptureConfig:
    iteration: str
    map_path: str
    mesh_path: str
    output_dir: Path
    source_scale: float = 1.0
    exposure_bias: float = 1.2
    light_scale: float = 5.0
    warmup_ticks: int = 35


class LivingCharacterBindQACaptureDriver:
    def __init__(self, config: LivingCharacterBindQACaptureConfig):
        self.config = config
        self.camera, self.heights = self._build_scene()
        self.output = config.output_dir / "front-left45-profile.png"
        self.started = time.monotonic()
        self.warmup = config.warmup_ticks
        self.requested = False
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def _build_scene(self):
        config = self.config
        if config.output_dir.exists() or unreal.EditorAssetLibrary.does_asset_exist(config.map_path):
            raise RuntimeError("refusing to overwrite immutable bind-pose QA")
        mesh = unreal.load_asset(config.mesh_path)
        if mesh is None:
            raise RuntimeError(f"required mesh unavailable: {config.mesh_path}")
        config.output_dir.mkdir(parents=True)
        if not unreal.EditorLevelLibrary.new_level(config.map_path):
            raise RuntimeError("failed to create bind-pose QA map")

        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        characters = []
        for label, x, yaw in (("front", -95.0, 0.0), ("left45", 0.0, 45.0), ("profile", 95.0, 90.0)):
            actor = actors.spawn_actor_from_class(
                unreal.SkeletalMeshActor,
                unreal.Vector(x, 0.0, 0.0),
                unreal.Rotator(roll=0.0, pitch=0.0, yaw=yaw),
            )
            actor.set_actor_label(f"Character_{label}_{config.iteration}")
            actor.set_actor_scale3d(unreal.Vector(config.source_scale, config.source_scale, config.source_scale))
            actor.get_component_by_class(unreal.SkeletalMeshComponent).set_editor_property(
                "skeletal_mesh_asset", mesh
            )
            characters.append(actor)

        bounds = [actor.get_actor_bounds(False, True) for actor in characters]
        heights = [extent.z * 2.0 for _, extent in bounds]
        if any(not 80.0 <= height <= 260.0 for height in heights):
            raise RuntimeError(f"unexpected character heights: {heights}")
        target = unreal.Vector(0.0, 0.0, sum(origin.z for origin, _ in bounds) / len(bounds))
        camera_location = target + unreal.Vector(0.0, 780.0, 0.0)
        camera = actors.spawn_actor_from_class(
            unreal.CineCameraActor,
            camera_location,
            unreal.MathLibrary.find_look_at_rotation(camera_location, target),
        )
        camera.camera_component.set_editor_property("current_focal_length", 48.0)
        camera.camera_component.set_editor_property("current_aperture", 8.0)

        for offset, base_intensity in (
            (unreal.Vector(-240, 260, 150), 2600.0),
            (unreal.Vector(240, 220, 70), 1600.0),
            (unreal.Vector(0, -220, 140), 2200.0),
        ):
            location = target + offset
            light = actors.spawn_actor_from_class(
                unreal.RectLight, location, unreal.MathLibrary.find_look_at_rotation(location, target)
            )
            component = light.get_component_by_class(unreal.RectLightComponent)
            component.set_editor_property("intensity", base_intensity * config.light_scale)
            component.set_editor_property("source_width", 150.0)
            component.set_editor_property("source_height", 180.0)

        sky = actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector())
        sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("intensity", 1.0)
        post = actors.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector())
        post.set_editor_property("unbound", True)
        settings = post.get_editor_property("settings")
        settings.set_editor_property("override_auto_exposure_method", True)
        settings.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)
        settings.set_editor_property("override_auto_exposure_bias", True)
        settings.set_editor_property("auto_exposure_bias", config.exposure_bias)
        settings.set_editor_property("override_motion_blur_amount", True)
        settings.set_editor_property("motion_blur_amount", 0.0)
        post.set_editor_property("settings", settings)
        if not unreal.EditorLevelLibrary.save_current_level():
            raise RuntimeError("failed to save bind-pose QA map")
        return camera, heights

    def tick(self, _delta):
        if self.warmup:
            self.warmup -= 1
            return
        if not self.requested:
            self.requested = True
            unreal.AutomationLibrary.take_high_res_screenshot(1920, 1080, str(self.output), self.camera)
            return
        if self.output.is_file() and self.output.stat().st_size > 24:
            report = {
                "schemaVersion": 1,
                "iteration": self.config.iteration,
                "status": "captured-draft-bind-pose-evidence",
                "map": self.config.map_path,
                "mesh": self.config.mesh_path,
                "heightCm": self.heights,
                "views": ["front", "left45", "profile"],
                "frame": {
                    "file": str(self.output),
                    "bytes": self.output.stat().st_size,
                    "sha256": hashlib.sha256(self.output.read_bytes()).hexdigest(),
                },
                "visualValidationPending": True,
                "humanApproved": False,
                "releaseEligible": False,
            }
            (self.config.output_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n")
            unreal.unregister_slate_post_tick_callback(self.handle)
            unreal.EditorPythonScripting.set_keep_python_script_alive(False)
            unreal.SystemLibrary.quit_editor()
        elif time.monotonic() - self.started > 180:
            raise RuntimeError(f"bind capture timed out: {self.output}")


def capture_living_character_bind(config: LivingCharacterBindQACaptureConfig):
    unreal.EditorPythonScripting.set_keep_python_script_alive(True)
    return LivingCharacterBindQACaptureDriver(config)
