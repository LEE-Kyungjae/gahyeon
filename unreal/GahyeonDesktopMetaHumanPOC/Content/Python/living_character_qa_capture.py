"""Reusable fail-closed UE 5.8 fixed-camera character comparison capture."""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import time

import unreal


@dataclass(frozen=True)
class LivingCharacterQACaptureConfig:
    iteration: str
    map_path: str
    mesh_path: str
    animation_path: str
    output_dir: Path
    source_scale: float
    camera_distance_cm: float = 850.0
    focal_length_mm: float = 35.0
    exposure_bias: float = 0.0
    warmup_ticks: int = 30


def _require_asset(path):
    asset = unreal.load_asset(path)
    if asset is None:
        raise RuntimeError(f"required asset unavailable: {path}")
    return asset


def _add_rect_light(actors, label, location, target, intensity):
    light = actors.spawn_actor_from_class(
        unreal.RectLight, location, unreal.MathLibrary.find_look_at_rotation(location, target)
    )
    light.set_actor_label(label)
    component = light.get_component_by_class(unreal.RectLightComponent)
    component.set_editor_property("intensity", intensity)
    component.set_editor_property("source_width", 110.0)
    component.set_editor_property("source_height", 130.0)


def _build_scene(config):
    if config.output_dir.exists():
        raise RuntimeError(f"refusing to overwrite immutable evidence: {config.output_dir}")
    if unreal.EditorAssetLibrary.does_asset_exist(config.map_path):
        raise RuntimeError(f"refusing to overwrite immutable map: {config.map_path}")
    config.output_dir.mkdir(parents=True)
    mesh = _require_asset(config.mesh_path)
    animation = _require_asset(config.animation_path)
    if not unreal.EditorLevelLibrary.new_level(config.map_path):
        raise RuntimeError("failed to create character QA map")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    characters = []
    for role, x in (("Reference", -55.0), ("Animated", 55.0)):
        actor = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(x, 0, 0))
        actor.set_actor_label(f"Character_{role}_{config.iteration}")
        actor.set_actor_scale3d(
            unreal.Vector(config.source_scale, config.source_scale, config.source_scale)
        )
        actor.get_component_by_class(unreal.SkeletalMeshComponent).set_editor_property(
            "skeletal_mesh_asset", mesh
        )
        characters.append(actor)
    animated = characters[1].get_component_by_class(unreal.SkeletalMeshComponent)
    animated.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    animated.play_animation(animation, True)
    animated.set_position(0.5, False)

    bounds = [actor.get_actor_bounds(False, True) for actor in characters]
    heights = [extent.z * 2.0 for _, extent in bounds]
    if any(not 80.0 <= value <= 260.0 for value in heights):
        raise RuntimeError(f"unexpected normalized character heights: {heights}")
    target = unreal.Vector(
        sum(origin.x for origin, _ in bounds) / len(bounds),
        sum(origin.y for origin, _ in bounds) / len(bounds),
        sum(origin.z for origin, _ in bounds) / len(bounds),
    )
    camera_location = target + unreal.Vector(0.0, config.camera_distance_cm, 0.0)
    camera = actors.spawn_actor_from_class(
        unreal.CineCameraActor,
        camera_location,
        unreal.MathLibrary.find_look_at_rotation(camera_location, target),
    )
    camera.set_actor_label(f"CAM_CharacterCompare_{config.iteration}")
    camera.camera_component.set_editor_property("current_focal_length", config.focal_length_mm)
    camera.camera_component.set_editor_property("current_aperture", 5.6)
    _add_rect_light(actors, f"KEY_{config.iteration}", target + unreal.Vector(-150, 210, 110), target, 1800)
    _add_rect_light(actors, f"FILL_{config.iteration}", target + unreal.Vector(150, 170, 45), target, 900)
    _add_rect_light(actors, f"RIM_{config.iteration}", target + unreal.Vector(0, -160, 100), target, 1400)
    sky = actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector())
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("intensity", 0.5)
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
        raise RuntimeError("failed to save character QA map")
    return camera, heights


class LivingCharacterQACaptureDriver:
    def __init__(self, config):
        self.config = config
        self.camera, self.heights = _build_scene(config)
        self.output = config.output_dir / "reference-vs-animation.png"
        self.started = time.monotonic()
        self.warmup = config.warmup_ticks
        self.requested = False
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def tick(self, _delta):
        if self.warmup:
            self.warmup -= 1
            return
        if not self.requested:
            self.requested = True
            unreal.AutomationLibrary.take_high_res_screenshot(
                1600, 1200, str(self.output), self.camera
            )
            return
        if self.output.is_file() and self.output.stat().st_size > 24:
            report = {
                "schemaVersion": 1,
                "iteration": self.config.iteration,
                "status": "captured-draft-character-comparison",
                "map": self.config.map_path,
                "mesh": self.config.mesh_path,
                "animation": self.config.animation_path,
                "sourceScaleApplied": self.config.source_scale,
                "heightCm": self.heights,
                "camera": {
                    "distanceCm": self.config.camera_distance_cm,
                    "focalLengthMm": self.config.focal_length_mm,
                    "exposureBias": self.config.exposure_bias,
                },
                "frame": {
                    "file": str(self.output),
                    "bytes": self.output.stat().st_size,
                    "sha256": hashlib.sha256(self.output.read_bytes()).hexdigest(),
                },
                "visualValidationPending": True,
                "humanApproved": False,
                "releaseEligible": False,
            }
            (self.config.output_dir / "report.json").write_text(
                json.dumps(report, indent=2) + "\n"
            )
            unreal.unregister_slate_post_tick_callback(self.handle)
            unreal.log("LIVING_CHARACTER_CAPTURE=" + json.dumps(report, sort_keys=True))
            unreal.SystemLibrary.quit_editor()
        elif time.monotonic() - self.started > 180:
            raise RuntimeError(f"character capture timed out: {self.output}")


def capture_living_character_comparison(config):
    return LivingCharacterQACaptureDriver(config)
