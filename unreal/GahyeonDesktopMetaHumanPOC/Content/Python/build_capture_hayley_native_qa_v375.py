"""Build and capture an immutable reference-versus-native-animation Hayley QA view."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time

import unreal


MAP = "/Game/LivingCharacterPOC/v375/QA/L_HayleyNativeCompare_v375"
MESH = "/Game/LivingCharacterPOC/v371/Characters/Hayley/Hayley2"
ANIMATION = "/Game/LivingCharacterPOC/v371/Characters/Hayley/Hayley2_Anim"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v375-hayley-native-qa"
)
_driver = None


def require_asset_v375(path: str):
    asset = unreal.load_asset(path)
    if asset is None:
        raise RuntimeError(f"required asset unavailable: {path}")
    return asset


def add_rect_light_v375(actors, label, location, target, intensity):
    light = actors.spawn_actor_from_class(
        unreal.RectLight, location, unreal.MathLibrary.find_look_at_rotation(location, target)
    )
    light.set_actor_label(label)
    component = light.get_component_by_class(unreal.RectLightComponent)
    component.set_editor_property("intensity", intensity)
    component.set_editor_property("source_width", 100.0)
    component.set_editor_property("source_height", 120.0)


def build_hayley_native_qa_v375():
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to overwrite immutable evidence: {OUTPUT}")
    if unreal.EditorAssetLibrary.does_asset_exist(MAP):
        raise RuntimeError(f"refusing to overwrite immutable map: {MAP}")
    OUTPUT.mkdir(parents=True)
    mesh = require_asset_v375(MESH)
    animation = require_asset_v375(ANIMATION)
    if not unreal.EditorLevelLibrary.new_level(MAP):
        raise RuntimeError("failed to create Hayley native QA map")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    characters = []
    for label, x in (("Hayley_Reference_v375", -55.0), ("Hayley_NativeAnim_v375", 55.0)):
        actor = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(x, 0, 0))
        actor.set_actor_label(label)
        component = actor.get_component_by_class(unreal.SkeletalMeshComponent)
        component.set_editor_property("skeletal_mesh_asset", mesh)
        characters.append(actor)
    animated = characters[1].get_component_by_class(unreal.SkeletalMeshComponent)
    animated.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    animated.play_animation(animation, True)
    animated.set_position(0.5, False)

    origin, extent = characters[0].get_actor_bounds(False, True)
    height = extent.z * 2.0
    if not 80.0 <= height <= 260.0:
        raise RuntimeError(f"unexpected Hayley height: {height}")
    target = unreal.Vector(0.0, origin.y, origin.z)
    camera_location = target + unreal.Vector(0.0, 500.0, 0.0)
    camera = actors.spawn_actor_from_class(
        unreal.CineCameraActor,
        camera_location,
        unreal.MathLibrary.find_look_at_rotation(camera_location, target),
    )
    camera.set_actor_label("CAM_HayleyNativeCompare_v375")
    camera.camera_component.set_editor_property("current_focal_length", 50.0)
    camera.camera_component.set_editor_property("current_aperture", 5.6)
    add_rect_light_v375(actors, "KEY_Hayley_v375", target + unreal.Vector(-120, 180, 90), target, 4500)
    add_rect_light_v375(actors, "FILL_Hayley_v375", target + unreal.Vector(130, 150, 30), target, 2600)
    add_rect_light_v375(actors, "RIM_Hayley_v375", target + unreal.Vector(0, -130, 80), target, 3000)
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
        raise RuntimeError("failed to save Hayley native QA map")
    return camera, height


class CaptureDriverV375:
    def __init__(self):
        self.camera, self.height = build_hayley_native_qa_v375()
        self.output = OUTPUT / "hayley-reference-vs-native.png"
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
                1600, 1200, str(self.output), self.camera
            )
            return
        if self.output.is_file() and self.output.stat().st_size > 24:
            digest = hashlib.sha256(self.output.read_bytes()).hexdigest()
            report = {
                "schemaVersion": 1,
                "iteration": "v375",
                "status": "captured-draft-native-animation-comparison",
                "map": MAP,
                "mesh": MESH,
                "animation": ANIMATION,
                "heightCm": self.height,
                "frame": {
                    "file": str(self.output),
                    "bytes": self.output.stat().st_size,
                    "sha256": digest,
                },
                "knownImportFinding": "Hayley source bind pose was invalid and Unreal rebound skinning to time-zero pose.",
                "visualValidationPending": True,
                "humanApproved": False,
                "releaseEligible": False,
            }
            (OUTPUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
            unreal.unregister_slate_post_tick_callback(self.handle)
            unreal.log("HAYLEY_V375_CAPTURE=" + json.dumps(report, sort_keys=True))
            unreal.SystemLibrary.quit_editor()
        elif time.monotonic() - self.started > 180:
            raise RuntimeError(f"Hayley capture timed out: {self.output}")


def capture_hayley_native_qa_v375():
    global _driver
    if _driver is not None:
        raise RuntimeError("Hayley capture already running")
    _driver = CaptureDriverV375()


capture_hayley_native_qa_v375()
