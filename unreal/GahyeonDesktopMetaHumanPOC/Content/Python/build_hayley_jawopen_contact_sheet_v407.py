"""Render neutral/open/return poses from Hayley's isolated jawOpen proof."""

import hashlib
import json
from pathlib import Path
import time

import unreal


MAP = "/Game/LivingCharacterPOC/v407/QA/L_HayleyJawOpenSheet_v407"
MESH = "/Game/LivingCharacterPOC/v406/JawOpenImport/Hayley_JawOpen_v405"
ANIMATION = "/Game/LivingCharacterPOC/v406/JawOpenImport/Hayley_JawOpen_v405_Anim"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v407-hayley-jawopen-contact-sheet"
)
POSES = (("neutral", 0.0), ("jaw-open-18deg", 0.5), ("neutral-return", 1.0))
_driver = None


def require_asset_v407(path):
    asset = unreal.load_asset(path)
    if asset is None:
        raise RuntimeError(f"required asset unavailable: {path}")
    return asset


def add_light_v407(actors, location, target, intensity):
    light = actors.spawn_actor_from_class(
        unreal.RectLight, location, unreal.MathLibrary.find_look_at_rotation(location, target)
    )
    component = light.get_component_by_class(unreal.RectLightComponent)
    component.set_editor_property("intensity", intensity)
    component.set_editor_property("source_width", 100.0)
    component.set_editor_property("source_height", 110.0)


def build_hayley_jawopen_contact_sheet_v407():
    if OUTPUT.exists() or unreal.EditorAssetLibrary.does_asset_exist(MAP):
        raise RuntimeError("refusing to overwrite immutable v407 evidence")
    unreal.EditorPythonScripting.set_keep_python_script_alive(True)
    OUTPUT.mkdir(parents=True)
    mesh = require_asset_v407(MESH)
    animation = require_asset_v407(ANIMATION)
    if not unreal.EditorLevelLibrary.new_level(MAP):
        raise RuntimeError("failed to create v407 map")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    characters = []
    for x, (label, position) in zip((-78.0, 0.0, 78.0), POSES):
        actor = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(x, 0, 0))
        actor.set_actor_label(f"Hayley_{label}_v407")
        actor.set_actor_scale3d(unreal.Vector(0.1, 0.1, 0.1))
        component = actor.get_component_by_class(unreal.SkeletalMeshComponent)
        component.set_editor_property("skeletal_mesh_asset", mesh)
        component.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
        component.play_animation(animation, True)
        component.set_position(position, False)
        component.set_editor_property("global_anim_rate_scale", 0.0)
        characters.append(actor)
    bounds = [actor.get_actor_bounds(False, True) for actor in characters]
    target = unreal.Vector(0, 0, bounds[0][0].z + bounds[0][1].z * 0.58)
    camera_location = target + unreal.Vector(0, 330, 0)
    camera = actors.spawn_actor_from_class(
        unreal.CineCameraActor, camera_location,
        unreal.MathLibrary.find_look_at_rotation(camera_location, target),
    )
    camera.camera_component.set_editor_property("current_focal_length", 50.0)
    camera.camera_component.set_editor_property("current_aperture", 8.0)
    add_light_v407(actors, target + unreal.Vector(-120, 140, 70), target, 2200)
    add_light_v407(actors, target + unreal.Vector(120, 120, 30), target, 1300)
    add_light_v407(actors, target + unreal.Vector(0, -120, 70), target, 1600)
    sky = actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector())
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("intensity", 0.7)
    post = actors.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector())
    post.set_editor_property("unbound", True)
    settings = post.get_editor_property("settings")
    settings.set_editor_property("override_auto_exposure_method", True)
    settings.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)
    settings.set_editor_property("override_auto_exposure_bias", True)
    settings.set_editor_property("auto_exposure_bias", 0.9)
    settings.set_editor_property("override_motion_blur_amount", True)
    settings.set_editor_property("motion_blur_amount", 0.0)
    post.set_editor_property("settings", settings)
    if not unreal.EditorLevelLibrary.save_current_level():
        raise RuntimeError("failed to save v407 map")
    return camera


class HayleyJawOpenSheetDriverV407:
    def __init__(self):
        self.camera = build_hayley_jawopen_contact_sheet_v407()
        self.output = OUTPUT / "hayley-neutral-open-return.png"
        self.warmup = 30
        self.requested = False
        self.started = time.monotonic()
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

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
                "iteration": "v407",
                "status": "captured-draft-isolated-jawopen-contact-sheet",
                "map": MAP,
                "mesh": MESH,
                "animation": ANIMATION,
                "poses": [{"label": label, "positionSeconds": value} for label, value in POSES],
                "frame": {
                    "file": str(self.output),
                    "bytes": self.output.stat().st_size,
                    "sha256": hashlib.sha256(self.output.read_bytes()).hexdigest(),
                },
                "visualValidationPending": True,
                "humanApproved": False,
                "releaseEligible": False,
            }
            (OUTPUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
            unreal.unregister_slate_post_tick_callback(self.handle)
            unreal.EditorPythonScripting.set_keep_python_script_alive(False)
            unreal.log("HAYLEY_V407_JAWOPEN_SHEET=" + json.dumps(report, sort_keys=True))
            unreal.SystemLibrary.quit_editor()
        elif time.monotonic() - self.started > 180:
            unreal.EditorPythonScripting.set_keep_python_script_alive(False)
            raise RuntimeError("v407 capture timed out")


def capture_hayley_jawopen_contact_sheet_v407():
    global _driver
    _driver = HayleyJawOpenSheetDriverV407()


capture_hayley_jawopen_contact_sheet_v407()
