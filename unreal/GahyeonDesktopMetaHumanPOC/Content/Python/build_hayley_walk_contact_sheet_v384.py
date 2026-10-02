"""Render four frozen phases of the retargeted Hayley walk plus reference pose."""

import hashlib
import json
from pathlib import Path
import time

import unreal


MAP = "/Game/LivingCharacterPOC/v384/QA/L_HayleyWalkContactSheet_v384"
MESH = "/Game/LivingCharacterPOC/v371/Characters/Hayley/Hayley2"
ANIMATION = "/Game/LivingCharacterPOC/v382/Animation/AS_Hayley_GynoidWalk_v382"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v384-hayley-walk-contact-sheet"
)
PHASES = (0.0, 0.25, 0.5, 0.75)
_driver = None


def require_asset_v384(path):
    asset = unreal.load_asset(path)
    if asset is None:
        raise RuntimeError(f"required asset unavailable: {path}")
    return asset


def add_rect_light_v384(actors, label, location, target, intensity):
    light = actors.spawn_actor_from_class(
        unreal.RectLight, location, unreal.MathLibrary.find_look_at_rotation(location, target)
    )
    light.set_actor_label(label)
    component = light.get_component_by_class(unreal.RectLightComponent)
    component.set_editor_property("intensity", intensity)
    component.set_editor_property("source_width", 120.0)
    component.set_editor_property("source_height", 140.0)


def build_hayley_walk_contact_sheet_v384():
    if OUTPUT.exists() or unreal.EditorAssetLibrary.does_asset_exist(MAP):
        raise RuntimeError("refusing to overwrite immutable v384 evidence")
    OUTPUT.mkdir(parents=True)
    mesh = require_asset_v384(MESH)
    animation = require_asset_v384(ANIMATION)
    if not unreal.EditorLevelLibrary.new_level(MAP):
        raise RuntimeError("failed to create v384 map")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    all_characters = []
    reference = actors.spawn_actor_from_class(
        unreal.SkeletalMeshActor, unreal.Vector(-140.0, 0.0, 0.0)
    )
    reference.set_actor_label("Hayley_Reference_v384")
    reference.set_actor_scale3d(unreal.Vector(0.1, 0.1, 0.1))
    reference.get_component_by_class(unreal.SkeletalMeshComponent).set_editor_property(
        "skeletal_mesh_asset", mesh
    )
    all_characters.append(reference)
    for index, (x, phase) in enumerate(zip((-70.0, 0.0, 70.0, 140.0), PHASES)):
        actor = actors.spawn_actor_from_class(
            unreal.SkeletalMeshActor, unreal.Vector(x, 0.0, 0.0)
        )
        actor.set_actor_label(f"Hayley_Walk_{index}_{phase:.2f}s_v384")
        actor.set_actor_scale3d(unreal.Vector(0.1, 0.1, 0.1))
        component = actor.get_component_by_class(unreal.SkeletalMeshComponent)
        component.set_editor_property("skeletal_mesh_asset", mesh)
        component.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
        component.play_animation(animation, True)
        component.set_position(phase, False)
        component.set_editor_property("global_anim_rate_scale", 0.0)
        all_characters.append(actor)

    bounds = [actor.get_actor_bounds(False, True) for actor in all_characters]
    heights = [extent.z * 2.0 for _, extent in bounds]
    if any(not 80.0 <= value <= 260.0 for value in heights):
        raise RuntimeError(f"unexpected normalized heights: {heights}")
    target = unreal.Vector(0.0, 0.0, sum(origin.z for origin, _ in bounds) / len(bounds))
    camera_location = target + unreal.Vector(0.0, 650.0, 0.0)
    camera = actors.spawn_actor_from_class(
        unreal.CineCameraActor,
        camera_location,
        unreal.MathLibrary.find_look_at_rotation(camera_location, target),
    )
    camera.set_actor_label("CAM_HayleyWalkContactSheet_v384")
    camera.camera_component.set_editor_property("current_focal_length", 35.0)
    camera.camera_component.set_editor_property("current_aperture", 5.6)
    add_rect_light_v384(actors, "KEY_v384", target + unreal.Vector(-180, 220, 110), target, 2600)
    add_rect_light_v384(actors, "FILL_v384", target + unreal.Vector(180, 180, 55), target, 1500)
    add_rect_light_v384(actors, "RIM_v384", target + unreal.Vector(0, -170, 110), target, 1900)
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
        raise RuntimeError("failed to save v384 map")
    return camera, heights


class WalkContactSheetDriverV384:
    def __init__(self):
        self.camera, self.heights = build_hayley_walk_contact_sheet_v384()
        self.output = OUTPUT / "hayley-walk-phases.png"
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
                1920, 1080, str(self.output), self.camera
            )
            return
        if self.output.is_file() and self.output.stat().st_size > 24:
            report = {
                "schemaVersion": 1,
                "iteration": "v384",
                "status": "captured-draft-walk-phase-contact-sheet",
                "map": MAP,
                "mesh": MESH,
                "animation": ANIMATION,
                "phasesSeconds": PHASES,
                "heightCm": self.heights,
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
            unreal.log("HAYLEY_V384_WALK_SHEET=" + json.dumps(report, sort_keys=True))
            unreal.SystemLibrary.quit_editor()
        elif time.monotonic() - self.started > 180:
            raise RuntimeError(f"v384 capture timed out: {self.output}")


def capture_hayley_walk_contact_sheet_v384():
    global _driver
    if _driver is not None:
        raise RuntimeError("v384 capture already running")
    _driver = WalkContactSheetDriverV384()


capture_hayley_walk_contact_sheet_v384()
