"""Capture seven UE close-ups to select Hayley's actual jaw-open local axis."""

import hashlib
import json
from pathlib import Path
import time

import unreal


MAP = "/Game/LivingCharacterPOC/v392/QA/L_HayleyJawAxisCloseups_v392"
MESH = "/Game/LivingCharacterPOC/v391/JawAxisSweepImport/Hayley_JawAxisSweep_Full_v390"
ANIMATION = "/Game/LivingCharacterPOC/v391/JawAxisSweepImport/Hayley_JawAxisSweep_Full_v390_Anim"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v392-hayley-jaw-axis-closeups"
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


def require_asset_v392(path):
    asset = unreal.load_asset(path)
    if asset is None:
        raise RuntimeError(f"required asset unavailable: {path}")
    return asset


def add_rect_light_v392(actors, label, location, target, intensity):
    light = actors.spawn_actor_from_class(
        unreal.RectLight, location, unreal.MathLibrary.find_look_at_rotation(location, target)
    )
    light.set_actor_label(label)
    component = light.get_component_by_class(unreal.RectLightComponent)
    component.set_editor_property("intensity", intensity)
    component.set_editor_property("source_width", 80.0)
    component.set_editor_property("source_height", 100.0)


def build_hayley_jaw_axis_closeups_v392():
    if OUTPUT.exists() or unreal.EditorAssetLibrary.does_asset_exist(MAP):
        raise RuntimeError("refusing to overwrite immutable v392 evidence")
    OUTPUT.mkdir(parents=True)
    mesh = require_asset_v392(MESH)
    animation = require_asset_v392(ANIMATION)
    if not unreal.EditorLevelLibrary.new_level(MAP):
        raise RuntimeError("failed to create v392 QA map")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actor = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector())
    actor.set_actor_label("Hayley_JawAxisSweep_v392")
    actor.set_actor_scale3d(unreal.Vector(0.1, 0.1, 0.1))
    component = actor.get_component_by_class(unreal.SkeletalMeshComponent)
    component.set_editor_property("skeletal_mesh_asset", mesh)
    component.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    component.play_animation(animation, True)
    component.set_editor_property("global_anim_rate_scale", 0.0)
    origin, extent = actor.get_actor_bounds(False, True)
    height = extent.z * 2.0
    if not 80.0 <= height <= 260.0:
        raise RuntimeError(f"unexpected normalized height: {height}")
    target = unreal.Vector(origin.x, origin.y, origin.z + extent.z * 0.82)
    camera_location = target + unreal.Vector(0.0, 250.0, 0.0)
    camera = actors.spawn_actor_from_class(
        unreal.CineCameraActor,
        camera_location,
        unreal.MathLibrary.find_look_at_rotation(camera_location, target),
    )
    camera.set_actor_label("CAM_HayleyJawAxis_v392")
    camera.camera_component.set_editor_property("current_focal_length", 70.0)
    camera.camera_component.set_editor_property("current_aperture", 5.6)
    add_rect_light_v392(actors, "KEY_v392", target + unreal.Vector(-90, 110, 50), target, 3000)
    add_rect_light_v392(actors, "FILL_v392", target + unreal.Vector(100, 100, 15), target, 1800)
    add_rect_light_v392(actors, "RIM_v392", target + unreal.Vector(0, -100, 50), target, 2200)
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
        raise RuntimeError("failed to save v392 QA map")
    return camera, component, height


class JawAxisCaptureDriverV392:
    def __init__(self):
        self.camera, self.component, self.height = build_hayley_jaw_axis_closeups_v392()
        self.index = 0
        self.current_output = None
        self.requested = False
        self.settle = 0
        self.records = []
        self.started = time.monotonic()
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def tick(self, _delta):
        if self.index >= len(POSES):
            report = {
                "schemaVersion": 1,
                "iteration": "v392",
                "status": "captured-draft-jaw-axis-closeups",
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
            unreal.log("HAYLEY_V392_JAW_CLOSEUPS=" + json.dumps(report, sort_keys=True))
            unreal.SystemLibrary.quit_editor()
            return
        if self.current_output is None:
            label, position = POSES[self.index]
            self.component.set_position(position, False)
            self.current_output = OUTPUT / f"{self.index:02d}-{label}.png"
            self.settle = 8
            self.requested = False
            return
        if self.settle:
            self.settle -= 1
            return
        if not self.requested:
            self.requested = True
            unreal.AutomationLibrary.take_high_res_screenshot(
                1200, 1200, str(self.current_output), self.camera
            )
            return
        if self.current_output.is_file() and self.current_output.stat().st_size > 24:
            label, position = POSES[self.index]
            self.records.append({
                "label": label,
                "positionSeconds": position,
                "file": str(self.current_output),
                "sha256": hashlib.sha256(self.current_output.read_bytes()).hexdigest(),
            })
            self.index += 1
            self.current_output = None
        elif time.monotonic() - self.started > 240:
            raise RuntimeError("v392 jaw-axis capture timed out")


def capture_hayley_jaw_axis_closeups_v392():
    global _driver
    if _driver is not None:
        raise RuntimeError("v392 capture already running")
    _driver = JawAxisCaptureDriverV392()


capture_hayley_jaw_axis_closeups_v392()
