"""Spawn frozen Hayley actors with segmented motions before the first render evaluation."""

import hashlib
import json
from pathlib import Path
import time

import unreal


ITERATION = "v439"
MAP = "/Game/LivingCharacterPOC/v439/QA/L_HayleySegmentedSpawned_v439"
MESH = "/Game/LivingCharacterPOC/v371/Characters/Hayley/Hayley2"
ANIMATIONS = (
    ("explain", "/Game/LivingCharacterPOC/v435/Animation/AS_Hayley_HandsForwardSegmented_v435"),
    ("stand-sit", "/Game/LivingCharacterPOC/v436/Animation/AS_Hayley_StandSitSegmented_v436"),
)
OUTPUT = Path("/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v439-hayley-segmented-spawned")
SOURCE_SCALE = 0.1
EVALUATE_BEFORE_FREEZE = False
LIGHT_INTENSITY_SCALE = 1.0
EXPOSURE_BIAS = 1.0
CAMERA_DISTANCE = 920.0
PHASE_FRACTIONS = (0.1, 0.5, 0.9)
_driver = None


def require_v439(path):
    asset = unreal.load_asset(path)
    if asset is None:
        raise RuntimeError(f"required asset unavailable: {path}")
    return asset


def light_v439(actors, location, target, intensity):
    actor = actors.spawn_actor_from_class(unreal.RectLight, location, unreal.MathLibrary.find_look_at_rotation(location, target))
    component = actor.get_component_by_class(unreal.RectLightComponent)
    component.set_editor_property("intensity", intensity * LIGHT_INTENSITY_SCALE)
    component.set_editor_property("source_width", 160.0)
    component.set_editor_property("source_height", 180.0)


def build_v439():
    if OUTPUT.exists() or unreal.EditorAssetLibrary.does_asset_exist(MAP):
        raise RuntimeError("refusing to overwrite immutable v439 evidence")
    OUTPUT.mkdir(parents=True)
    mesh = require_v439(MESH)
    loaded = [(label, path, require_v439(path)) for label, path in ANIMATIONS]
    if not unreal.EditorLevelLibrary.new_level(MAP):
        raise RuntimeError("failed to create v439 map")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    records = []
    spawned = []
    phase_components = []
    pose_count = len(loaded) * len(PHASE_FRACTIONS)
    positions = tuple((index - (pose_count - 1) / 2.0) * 90.0 for index in range(pose_count))
    cursor = 0
    for label, path, animation in loaded:
        duration = float(animation.get_play_length())
        phases = tuple(duration * fraction for fraction in PHASE_FRACTIONS)
        for phase_index, phase in enumerate(phases):
            actor = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(positions[cursor], 0.0, 0.0))
            actor.set_actor_label(f"Hayley_{label}_{phase_index}_v439")
            actor.set_actor_scale3d(unreal.Vector(SOURCE_SCALE, SOURCE_SCALE, SOURCE_SCALE))
            component = actor.get_component_by_class(unreal.SkeletalMeshComponent)
            component.set_editor_property("skeletal_mesh_asset", mesh)
            if EVALUATE_BEFORE_FREEZE:
                component.override_animation_data(animation, True, False, phase, 0.0)
            else:
                component.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
                component.play_animation(animation, True)
                component.set_position(phase, False)
                component.set_editor_property("global_anim_rate_scale", 0.0)
            spawned.append(actor)
            cursor += 1
        records.append({"label": label, "animation": path, "durationSeconds": duration, "phasesSeconds": phases})
    bounds = [actor.get_actor_bounds(False, True) for actor in spawned]
    heights = [extent.z * 2.0 for _, extent in bounds]
    if any(not 80.0 <= value <= 260.0 for value in heights):
        raise RuntimeError(f"unexpected heights: {heights}")
    target = unreal.Vector(0.0, 0.0, sum(origin.z for origin, _ in bounds)/len(bounds))
    camera_location = target + unreal.Vector(0.0, CAMERA_DISTANCE, 0.0)
    camera = actors.spawn_actor_from_class(unreal.CineCameraActor, camera_location, unreal.MathLibrary.find_look_at_rotation(camera_location, target))
    camera.camera_component.set_editor_property("current_focal_length", 38.0)
    camera.camera_component.set_editor_property("current_aperture", 5.6)
    light_v439(actors, target + unreal.Vector(-260, 320, 140), target, 3400)
    light_v439(actors, target + unreal.Vector(260, 260, 80), target, 2200)
    light_v439(actors, target + unreal.Vector(0, -250, 140), target, 2400)
    sky = actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector())
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("intensity", 0.9)
    post = actors.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector())
    post.set_editor_property("unbound", True)
    settings = post.get_editor_property("settings")
    settings.set_editor_property("override_auto_exposure_method", True)
    settings.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)
    settings.set_editor_property("override_auto_exposure_bias", True)
    settings.set_editor_property("auto_exposure_bias", EXPOSURE_BIAS)
    settings.set_editor_property("override_motion_blur_amount", True)
    settings.set_editor_property("motion_blur_amount", 0.0)
    post.set_editor_property("settings", settings)
    if not unreal.EditorLevelLibrary.save_current_level():
        raise RuntimeError("failed to save v439 map")
    return camera, records, heights, phase_components


class SpawnedDriverV439:
    def __init__(self):
        self.camera, self.motion_records, self.heights, self.phase_components = build_v439()
        self.output = OUTPUT / "hayley-explain-and-stand-sit-phases.png"
        self.started = time.monotonic()
        self.warmup = 45
        self.requested = False
        self.freeze_step = 0
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def tick(self, _delta):
        if self.phase_components and self.freeze_step == 0:
            for component, phase in self.phase_components:
                component.set_position(phase, False)
            self.freeze_step = 1
            return
        if self.phase_components and self.freeze_step == 1:
            for component, _phase in self.phase_components:
                component.set_editor_property("global_anim_rate_scale", 0.0)
            self.freeze_step = 2
            return
        if self.warmup:
            self.warmup -= 1
            return
        if not self.requested:
            self.requested = True
            unreal.AutomationLibrary.take_high_res_screenshot(2560, 1080, str(self.output), self.camera)
            return
        if self.output.is_file() and self.output.stat().st_size > 24:
            report = {"schemaVersion": 1, "iteration": ITERATION, "status": "captured-draft-spawned-segmented-motion-evidence", "map": MAP, "mesh": MESH, "motions": self.motion_records, "heightCm": self.heights, "frame": {"file": str(self.output), "bytes": self.output.stat().st_size, "sha256": hashlib.sha256(self.output.read_bytes()).hexdigest()}, "visualValidationPending": True, "humanApproved": False, "releaseEligible": False}
            (OUTPUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
            unreal.unregister_slate_post_tick_callback(self.handle)
            unreal.EditorPythonScripting.set_keep_python_script_alive(False)
            unreal.SystemLibrary.quit_editor()
        elif time.monotonic() - self.started > 180:
            raise RuntimeError(f"v439 capture timed out: {self.output}")


def capture_hayley_segmented_spawned_v439():
    global _driver
    unreal.EditorPythonScripting.set_keep_python_script_alive(True)
    _driver = SpawnedDriverV439()


if __name__ == "__main__":
    capture_hayley_segmented_spawned_v439()
