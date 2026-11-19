"""Capture neutral, blink, and smile close-ups on clean Hayley in UE 5.8."""

import hashlib
import json
from pathlib import Path
import time

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
ITERATION = "v470"
MESH = "/Game/LivingCharacterPOC/v448/Characters/HayleyBindClean/Hayley_BindPoseClean_v447"
ANIMATION = "/Game/LivingCharacterPOC/v469/Animation/Hayley_CleanExpressionCalibration_v468"
MAP = "/Game/LivingCharacterPOC/v470/QA/L_HayleyCleanExpression_v470"
OUTPUT = ROOT / "artifacts/living-character-poc-v470-hayley-clean-expression-evidence"
POSES = (("neutral", 0.0), ("blink", 10.0 / 30.0), ("smile", 30.0 / 30.0))
OUTPUT_FILENAME = "hayley-neutral-blink-smile.png"
LIGHT_INTENSITY_SCALE = 1.0
EXPOSURE_BIAS = 1.2
_driver = None


def capture_hayley_clean_expression_v470():
    global _driver
    if OUTPUT.exists() or unreal.EditorAssetLibrary.does_asset_exist(MAP):
        raise RuntimeError("refusing to overwrite immutable v470 evidence")
    mesh = unreal.load_asset(MESH)
    animation = unreal.load_asset(ANIMATION)
    if mesh is None or animation is None:
        raise RuntimeError("clean expression dependencies are unavailable")
    if animation.get_editor_property("skeleton") != mesh.get_editor_property("skeleton"):
        raise RuntimeError("clean expression skeleton mismatch")
    OUTPUT.mkdir(parents=True)
    if not unreal.EditorLevelLibrary.new_level(MAP):
        raise RuntimeError("failed to create v470 map")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    characters = []
    for (label, position), x in zip(POSES, (-48.0, 0.0, 48.0)):
        actor = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(x, 0, 0))
        actor.set_actor_label(f"Hayley_{label}_v470")
        component = actor.get_component_by_class(unreal.SkeletalMeshComponent)
        component.set_editor_property("skeletal_mesh_asset", mesh)
        component.override_animation_data(animation, False, False, position, 0.0)
        characters.append(actor)
    bounds = [actor.get_actor_bounds(False, True) for actor in characters]
    if any(not 150.0 <= extent.z * 2.0 <= 190.0 for _, extent in bounds):
        raise RuntimeError(f"unexpected v470 heights: {[extent.z * 2.0 for _, extent in bounds]}")
    face_z = sum(origin.z + extent.z * 0.72 for origin, extent in bounds) / len(bounds)
    target = unreal.Vector(0, 0, face_z)
    camera_location = target + unreal.Vector(0, 285, 0)
    camera = actors.spawn_actor_from_class(
        unreal.CineCameraActor,
        camera_location,
        unreal.MathLibrary.find_look_at_rotation(camera_location, target),
    )
    camera.camera_component.set_editor_property("current_focal_length", 55.0)
    camera.camera_component.set_editor_property("current_aperture", 8.0)
    for offset, intensity in (
        (unreal.Vector(-120, 150, 80), 2600.0),
        (unreal.Vector(120, 120, 20), 1500.0),
        (unreal.Vector(0, -100, 70), 1900.0),
    ):
        location = target + offset
        light = actors.spawn_actor_from_class(
            unreal.RectLight, location, unreal.MathLibrary.find_look_at_rotation(location, target)
        )
        component = light.get_component_by_class(unreal.RectLightComponent)
        component.set_editor_property("intensity", intensity * LIGHT_INTENSITY_SCALE)
        component.set_editor_property("source_width", 90.0)
        component.set_editor_property("source_height", 110.0)
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
    unreal.EditorLevelLibrary.save_current_level()

    class Driver:
        def __init__(self):
            self.output = OUTPUT / OUTPUT_FILENAME
            self.warmup = 35
            self.requested = False
            self.started = time.monotonic()
            self.handle = unreal.register_slate_post_tick_callback(self.tick)

        def tick(self, _delta):
            if self.warmup:
                self.warmup -= 1
                return
            if not self.requested:
                self.requested = True
                unreal.AutomationLibrary.take_high_res_screenshot(1800, 1100, str(self.output), camera)
                return
            if self.output.is_file() and self.output.stat().st_size > 24:
                report = {
                    "schemaVersion": 1,
                    "iteration": ITERATION,
                    "status": "captured-draft-expression-evidence",
                    "mesh": MESH,
                    "animation": ANIMATION,
                    "poses": [{"label": label, "seconds": position} for label, position in POSES],
                    "frame": {
                        "file": str(self.output),
                        "bytes": self.output.stat().st_size,
                        "sha256": hashlib.sha256(self.output.read_bytes()).hexdigest(),
                    },
                    "humanApproved": False,
                    "releaseEligible": False,
                }
                (OUTPUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
                unreal.unregister_slate_post_tick_callback(self.handle)
                unreal.EditorPythonScripting.set_keep_python_script_alive(False)
                unreal.SystemLibrary.quit_editor()
            elif time.monotonic() - self.started > 180:
                raise RuntimeError("v470 expression capture timed out")

    unreal.EditorPythonScripting.set_keep_python_script_alive(True)
    _driver = Driver()


if __name__ == "__main__":
    capture_hayley_clean_expression_v470()
