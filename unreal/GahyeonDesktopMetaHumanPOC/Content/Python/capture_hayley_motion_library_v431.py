"""Capture fixed-camera evidence for Hayley's retargeted idle, gesture, and stand/sit clips."""

import hashlib
import json
from pathlib import Path
import time

import unreal


MAP = "/Game/LivingCharacterPOC/v431/QA/L_HayleyMotionLibrary_v431"
MESH = "/Game/LivingCharacterPOC/v371/Characters/Hayley/Hayley2"
ANIMATIONS = (
    ("idle", "/Game/LivingCharacterPOC/v428/Animation/AS_Hayley_CyberIdle_v428"),
    ("explain", "/Game/LivingCharacterPOC/v429/Animation/AS_Hayley_HandsForward_v429"),
    ("stand-sit", "/Game/LivingCharacterPOC/v430/Animation/AS_Hayley_StandSit_v430"),
)
OUTPUT = Path("/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v431-hayley-motion-library")
_driver = None


def require_asset_v431(path):
    asset = unreal.load_asset(path)
    if asset is None:
        raise RuntimeError(f"required asset unavailable: {path}")
    return asset


def add_rect_light_v431(actors, location, target, intensity):
    light = actors.spawn_actor_from_class(
        unreal.RectLight, location, unreal.MathLibrary.find_look_at_rotation(location, target)
    )
    component = light.get_component_by_class(unreal.RectLightComponent)
    component.set_editor_property("intensity", intensity)
    component.set_editor_property("source_width", 120.0)
    component.set_editor_property("source_height", 140.0)


def build_scene_v431():
    if OUTPUT.exists() or unreal.EditorAssetLibrary.does_asset_exist(MAP):
        raise RuntimeError("refusing to overwrite immutable v431 evidence")
    OUTPUT.mkdir(parents=True)
    mesh = require_asset_v431(MESH)
    animations = [(label, path, require_asset_v431(path)) for label, path in ANIMATIONS]
    if not unreal.EditorLevelLibrary.new_level(MAP):
        raise RuntimeError("failed to create v431 map")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    characters = []
    for index, x in enumerate((-90.0, 0.0, 90.0)):
        actor = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(x, 0.0, 0.0))
        actor.set_actor_label(f"Hayley_MotionPhase_{index}_v431")
        actor.set_actor_scale3d(unreal.Vector(0.1, 0.1, 0.1))
        component = actor.get_component_by_class(unreal.SkeletalMeshComponent)
        component.set_editor_property("skeletal_mesh_asset", mesh)
        component.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
        characters.append(component)
    bounds = [component.get_owner().get_actor_bounds(False, True) for component in characters]
    heights = [extent.z * 2.0 for _, extent in bounds]
    if any(not 80.0 <= value <= 260.0 for value in heights):
        raise RuntimeError(f"unexpected normalized heights: {heights}")
    target = unreal.Vector(0.0, 0.0, sum(origin.z for origin, _ in bounds) / len(bounds))
    camera_location = target + unreal.Vector(0.0, 580.0, 0.0)
    camera = actors.spawn_actor_from_class(
        unreal.CineCameraActor, camera_location,
        unreal.MathLibrary.find_look_at_rotation(camera_location, target),
    )
    camera.camera_component.set_editor_property("current_focal_length", 40.0)
    camera.camera_component.set_editor_property("current_aperture", 5.6)
    add_rect_light_v431(actors, target + unreal.Vector(-180, 220, 110), target, 2800)
    add_rect_light_v431(actors, target + unreal.Vector(180, 180, 55), target, 1700)
    add_rect_light_v431(actors, target + unreal.Vector(0, -170, 110), target, 1900)
    sky = actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector())
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("intensity", 0.8)
    post = actors.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector())
    post.set_editor_property("unbound", True)
    settings = post.get_editor_property("settings")
    settings.set_editor_property("override_auto_exposure_method", True)
    settings.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)
    settings.set_editor_property("override_auto_exposure_bias", True)
    settings.set_editor_property("auto_exposure_bias", 1.0)
    settings.set_editor_property("override_motion_blur_amount", True)
    settings.set_editor_property("motion_blur_amount", 0.0)
    post.set_editor_property("settings", settings)
    if not unreal.EditorLevelLibrary.save_current_level():
        raise RuntimeError("failed to save v431 map")
    return characters, camera, animations, heights


class MotionLibraryDriverV431:
    def __init__(self):
        self.components, self.camera, self.animations, self.heights = build_scene_v431()
        self.index = 0
        self.warmup = 30
        self.requested = False
        self.started = time.monotonic()
        self.records = []
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def configure(self):
        label, path, animation = self.animations[self.index]
        duration = float(animation.get_play_length())
        phases = (duration * 0.1, duration * 0.5, duration * 0.9)
        for component, phase in zip(self.components, phases):
            component.play_animation(animation, True)
            component.set_position(phase, False)
            component.set_editor_property("global_anim_rate_scale", 0.0)
        return label, path, duration, phases

    def tick(self, _delta):
        if self.warmup:
            self.warmup -= 1
            return
        label, path, duration, phases = self.configure()
        output = OUTPUT / f"hayley-{label}-phases.png"
        if not self.requested:
            self.requested = True
            unreal.AutomationLibrary.take_high_res_screenshot(1920, 1080, str(output), self.camera)
            return
        if output.is_file() and output.stat().st_size > 24:
            self.records.append({
                "label": label, "animation": path, "durationSeconds": duration,
                "phasesSeconds": phases, "file": str(output), "bytes": output.stat().st_size,
                "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            })
            self.index += 1
            self.requested = False
            self.warmup = 12
            if self.index < len(self.animations):
                return
            report = {
                "schemaVersion": 1, "iteration": "v431",
                "status": "captured-draft-hayley-motion-library",
                "map": MAP, "mesh": MESH, "heightCm": self.heights, "captures": self.records,
                "visualValidationPending": True, "humanApproved": False, "releaseEligible": False,
            }
            (OUTPUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
            unreal.unregister_slate_post_tick_callback(self.handle)
            unreal.EditorPythonScripting.set_keep_python_script_alive(False)
            unreal.SystemLibrary.quit_editor()
        elif time.monotonic() - self.started > 240:
            raise RuntimeError(f"v431 capture timed out: {output}")


def capture_hayley_motion_library_v431():
    global _driver
    if _driver is not None:
        raise RuntimeError("v431 capture already running")
    unreal.EditorPythonScripting.set_keep_python_script_alive(True)
    _driver = MotionLibraryDriverV431()


capture_hayley_motion_library_v431()
