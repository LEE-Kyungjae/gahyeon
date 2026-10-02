"""Render seven independently evaluated Hayley jaw poses in one QA scene."""

import hashlib
import json
from pathlib import Path
import time

import unreal


MAP = "/Game/LivingCharacterPOC/v402/QA/L_HayleyJawContactSheet_v402"
MESH = "/Game/LivingCharacterPOC/v391/JawAxisSweepImport/Hayley_JawAxisSweep_Full_v390"
ANIMATION = "/Game/LivingCharacterPOC/v391/JawAxisSweepImport/Hayley_JawAxisSweep_Full_v390_Anim"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v402-hayley-jaw-contact-sheet"
)
POSES = (
    ("neutral", 0.0),
    ("x-plus", 0.3),
    ("x-minus", 0.633333),
    ("y-plus", 0.966667),
    ("y-minus", 1.3),
    ("z-plus", 1.633333),
    ("z-minus", 1.966667),
)
_driver = None


def require_asset_v402(path):
    asset = unreal.load_asset(path)
    if asset is None:
        raise RuntimeError(f"required asset unavailable: {path}")
    return asset


def add_rect_light_v402(actors, location, target, intensity):
    light = actors.spawn_actor_from_class(
        unreal.RectLight, location, unreal.MathLibrary.find_look_at_rotation(location, target)
    )
    component = light.get_component_by_class(unreal.RectLightComponent)
    component.set_editor_property("intensity", intensity)
    component.set_editor_property("source_width", 150.0)
    component.set_editor_property("source_height", 130.0)


def build_hayley_jaw_contact_sheet_v402():
    if OUTPUT.exists() or unreal.EditorAssetLibrary.does_asset_exist(MAP):
        raise RuntimeError("refusing to overwrite immutable v402 evidence")
    unreal.EditorPythonScripting.set_keep_python_script_alive(True)
    OUTPUT.mkdir(parents=True)
    mesh = require_asset_v402(MESH)
    animation = require_asset_v402(ANIMATION)
    if not unreal.EditorLevelLibrary.new_level(MAP):
        raise RuntimeError("failed to create v402 map")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    characters = []
    x_positions = (-195.0, -130.0, -65.0, 0.0, 65.0, 130.0, 195.0)
    for x, (label, position) in zip(x_positions, POSES):
        actor = actors.spawn_actor_from_class(
            unreal.SkeletalMeshActor, unreal.Vector(x, 0.0, 0.0)
        )
        actor.set_actor_label(f"Hayley_Jaw_{label}_v402")
        actor.set_actor_scale3d(unreal.Vector(0.1, 0.1, 0.1))
        component = actor.get_component_by_class(unreal.SkeletalMeshComponent)
        component.set_editor_property("skeletal_mesh_asset", mesh)
        component.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
        component.play_animation(animation, True)
        component.set_position(position, False)
        component.set_editor_property("global_anim_rate_scale", 0.0)
        characters.append(actor)
    bounds = [actor.get_actor_bounds(False, True) for actor in characters]
    heights = [extent.z * 2.0 for _, extent in bounds]
    if any(not 80.0 <= value <= 260.0 for value in heights):
        raise RuntimeError(f"unexpected normalized heights: {heights}")
    average_z = sum(origin.z for origin, _ in bounds) / len(bounds)
    target = unreal.Vector(0.0, 0.0, average_z + bounds[0][1].z * 0.58)
    camera_location = target + unreal.Vector(0.0, 560.0, 0.0)
    camera = actors.spawn_actor_from_class(
        unreal.CineCameraActor,
        camera_location,
        unreal.MathLibrary.find_look_at_rotation(camera_location, target),
    )
    camera.camera_component.set_editor_property("current_focal_length", 42.0)
    camera.camera_component.set_editor_property("current_aperture", 8.0)
    add_rect_light_v402(actors, target + unreal.Vector(-220, 230, 100), target, 1900)
    add_rect_light_v402(actors, target + unreal.Vector(220, 190, 40), target, 1100)
    add_rect_light_v402(actors, target + unreal.Vector(0, -180, 100), target, 1500)
    sky = actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector())
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("intensity", 0.55)
    post = actors.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector())
    post.set_editor_property("unbound", True)
    settings = post.get_editor_property("settings")
    settings.set_editor_property("override_auto_exposure_method", True)
    settings.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)
    settings.set_editor_property("override_auto_exposure_bias", True)
    settings.set_editor_property("auto_exposure_bias", 0.25)
    settings.set_editor_property("override_motion_blur_amount", True)
    settings.set_editor_property("motion_blur_amount", 0.0)
    post.set_editor_property("settings", settings)
    if not unreal.EditorLevelLibrary.save_current_level():
        raise RuntimeError("failed to save v402 map")
    return camera, heights


class HayleyJawContactSheetDriverV402:
    def __init__(self):
        self.camera, self.heights = build_hayley_jaw_contact_sheet_v402()
        self.output = OUTPUT / "hayley-jaw-axis-poses.png"
        self.started = time.monotonic()
        self.warmup = 30
        self.requested = False
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def tick(self, _delta):
        if self.warmup:
            self.warmup -= 1
            return
        if not self.requested:
            self.requested = True
            unreal.AutomationLibrary.take_high_res_screenshot(
                2560, 1080, str(self.output), self.camera
            )
            return
        if self.output.is_file() and self.output.stat().st_size > 24:
            report = {
                "schemaVersion": 1,
                "iteration": "v402",
                "status": "captured-draft-independent-jaw-pose-contact-sheet",
                "map": MAP,
                "mesh": MESH,
                "animation": ANIMATION,
                "poses": [
                    {"label": label, "positionSeconds": position}
                    for label, position in POSES
                ],
                "heightCm": self.heights,
                "frame": {
                    "file": str(self.output),
                    "bytes": self.output.stat().st_size,
                    "sha256": hashlib.sha256(self.output.read_bytes()).hexdigest(),
                },
                "axisSelectionPending": True,
                "humanApproved": False,
                "releaseEligible": False,
            }
            (OUTPUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
            unreal.unregister_slate_post_tick_callback(self.handle)
            unreal.EditorPythonScripting.set_keep_python_script_alive(False)
            unreal.log("HAYLEY_V402_JAW_SHEET=" + json.dumps(report, sort_keys=True))
            unreal.SystemLibrary.quit_editor()
        elif time.monotonic() - self.started > 180:
            unreal.EditorPythonScripting.set_keep_python_script_alive(False)
            raise RuntimeError(f"v402 capture timed out: {self.output}")


def capture_hayley_jaw_contact_sheet_v402():
    global _driver
    if _driver is not None:
        raise RuntimeError("v402 capture already running")
    _driver = HayleyJawContactSheetDriverV402()


capture_hayley_jaw_contact_sheet_v402()
