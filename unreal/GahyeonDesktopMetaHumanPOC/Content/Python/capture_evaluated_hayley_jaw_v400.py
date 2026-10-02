"""Build a fresh QA scene and capture one-tick-evaluated Hayley jaw poses."""

import hashlib
import json
from pathlib import Path
import time

import unreal


MAP = "/Game/LivingCharacterPOC/v400/QA/L_HayleyEvaluatedJaw_v400"
MESH = "/Game/LivingCharacterPOC/v391/JawAxisSweepImport/Hayley_JawAxisSweep_Full_v390"
ANIMATION = "/Game/LivingCharacterPOC/v391/JawAxisSweepImport/Hayley_JawAxisSweep_Full_v390_Anim"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v400-hayley-evaluated-jaw"
)
POSES = (
    ("neutral", 0.0),
    ("jaw-x-plus-5", 0.3),
    ("jaw-x-minus-5", 0.633333),
    ("jaw-y-plus-5", 0.966667),
    ("jaw-y-minus-5", 1.3),
    ("jaw-z-plus-5", 1.633333),
    ("jaw-z-minus-5", 1.966667),
)
_driver = None


def require_asset_v400(path):
    asset = unreal.load_asset(path)
    if asset is None:
        raise RuntimeError(f"required asset unavailable: {path}")
    return asset


def add_light_v400(actors, label, location, target, intensity):
    light = actors.spawn_actor_from_class(
        unreal.RectLight, location, unreal.MathLibrary.find_look_at_rotation(location, target)
    )
    light.set_actor_label(label)
    component = light.get_component_by_class(unreal.RectLightComponent)
    component.set_editor_property("intensity", intensity)
    component.set_editor_property("source_width", 70.0)
    component.set_editor_property("source_height", 70.0)


def build_scene_v400():
    if OUTPUT.exists() or unreal.EditorAssetLibrary.does_asset_exist(MAP):
        raise RuntimeError("refusing to overwrite immutable v400 evidence")
    OUTPUT.mkdir(parents=True)
    mesh = require_asset_v400(MESH)
    animation = require_asset_v400(ANIMATION)
    if not unreal.EditorLevelLibrary.new_level(MAP):
        raise RuntimeError("failed to create v400 QA map")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actor = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector())
    actor.set_actor_label("Hayley_EvaluatedJaw_v400")
    actor.set_actor_scale3d(unreal.Vector(0.1, 0.1, 0.1))
    component = actor.get_component_by_class(unreal.SkeletalMeshComponent)
    component.set_editor_property("skeletal_mesh_asset", mesh)
    component.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    component.play_animation(animation, True)
    origin, extent = actor.get_actor_bounds(False, True)
    height = extent.z * 2.0
    if not 80.0 <= height <= 260.0:
        raise RuntimeError(f"unexpected normalized height: {height}")
    target = unreal.Vector(origin.x, origin.y, origin.z + extent.z * 0.86)
    camera_location = target + unreal.Vector(0.0, 165.0, 0.0)
    camera = actors.spawn_actor_from_class(
        unreal.CineCameraActor,
        camera_location,
        unreal.MathLibrary.find_look_at_rotation(camera_location, target),
    )
    camera.set_actor_label("CAM_HayleyEvaluatedJaw_v400")
    camera.camera_component.set_editor_property("current_focal_length", 70.0)
    camera.camera_component.set_editor_property("current_aperture", 8.0)
    add_light_v400(actors, "KEY_v400", target + unreal.Vector(-75, 90, 40), target, 850)
    add_light_v400(actors, "FILL_v400", target + unreal.Vector(85, 80, 10), target, 350)
    add_light_v400(actors, "RIM_v400", target + unreal.Vector(0, -90, 45), target, 500)
    sky = actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector())
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("intensity", 0.25)
    post = actors.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector())
    post.set_editor_property("unbound", True)
    settings = post.get_editor_property("settings")
    settings.set_editor_property("override_auto_exposure_method", True)
    settings.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)
    settings.set_editor_property("override_auto_exposure_bias", True)
    settings.set_editor_property("auto_exposure_bias", -1.0)
    settings.set_editor_property("override_motion_blur_amount", True)
    settings.set_editor_property("motion_blur_amount", 0.0)
    post.set_editor_property("settings", settings)
    if not unreal.EditorLevelLibrary.save_current_level():
        raise RuntimeError("failed to save v400 QA map")
    return component, camera, height


class EvaluatedJawCaptureV400:
    def __init__(self):
        self.component, self.camera, self.height = build_scene_v400()
        self.index = 0
        self.phase = "position"
        self.output = None
        self.settle = 0
        self.records = []
        self.started = time.monotonic()
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def tick(self, _delta):
        if self.index >= len(POSES):
            report = {
                "schemaVersion": 1,
                "iteration": "v400",
                "status": "captured-draft-one-tick-evaluated-jaw-axis",
                "map": MAP,
                "mesh": MESH,
                "animation": ANIMATION,
                "heightCm": self.height,
                "frames": self.records,
                "axisSelectionPending": True,
                "humanApproved": False,
                "releaseEligible": False,
            }
            (OUTPUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
            unreal.unregister_slate_post_tick_callback(self.handle)
            unreal.log("HAYLEY_V400_EVALUATED_JAW=" + json.dumps(report, sort_keys=True))
            unreal.SystemLibrary.quit_editor()
            return
        label, position = POSES[self.index]
        if self.phase == "position":
            self.component.set_editor_property("global_anim_rate_scale", 1.0)
            self.component.set_position(position, False)
            self.phase = "freeze"
            return
        if self.phase == "freeze":
            self.component.set_editor_property("global_anim_rate_scale", 0.0)
            self.output = OUTPUT / f"{self.index:02d}-{label}.png"
            self.settle = 8
            self.phase = "settle"
            return
        if self.phase == "settle":
            if self.settle:
                self.settle -= 1
                return
            unreal.AutomationLibrary.take_high_res_screenshot(
                1200, 1200, str(self.output), self.camera
            )
            self.phase = "wait"
            return
        if self.phase == "wait":
            if self.output.is_file() and self.output.stat().st_size > 24:
                self.records.append({
                    "label": label,
                    "requestedPositionSeconds": position,
                    "file": str(self.output),
                    "sha256": hashlib.sha256(self.output.read_bytes()).hexdigest(),
                })
                self.index += 1
                self.phase = "position"
            elif time.monotonic() - self.started > 240:
                raise RuntimeError("v400 jaw capture timed out")


def capture_evaluated_jaw_v400():
    global _driver
    if _driver is not None:
        raise RuntimeError("v400 capture already running")
    _driver = EvaluatedJawCaptureV400()


capture_evaluated_jaw_v400()
