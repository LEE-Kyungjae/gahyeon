"""Capture immutable UE evidence for the action-free Hayley bind pose."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import time

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
ITERATION = os.environ.get("GAHYEON_HAYLEY_BIND_CAPTURE_ITERATION", "v449")
MESH = "/Game/LivingCharacterPOC/v448/Characters/HayleyBindClean/Hayley_BindPoseClean_v447"
MAP = f"/Game/LivingCharacterPOC/{ITERATION}/QA/L_HayleyCleanBind_{ITERATION}"
OUTPUT = ROOT / f"artifacts/living-character-poc-{ITERATION}-hayley-clean-bind-ue-qa"


def capture_hayley_clean_bind_v449():
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to overwrite immutable evidence: {OUTPUT}")
    if unreal.EditorAssetLibrary.does_asset_exist(MAP):
        raise RuntimeError(f"refusing to overwrite immutable map: {MAP}")
    mesh = unreal.load_asset(MESH)
    if mesh is None:
        raise RuntimeError(f"missing clean Hayley mesh: {MESH}")
    OUTPUT.mkdir(parents=True)
    if not unreal.EditorLevelLibrary.new_level(MAP):
        raise RuntimeError("failed to create clean-bind QA map")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    character = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector())
    character.set_actor_label("Hayley_CleanBind_v449")
    component = character.get_component_by_class(unreal.SkeletalMeshComponent)
    component.set_editor_property("skeletal_mesh_asset", mesh)
    origin, extent = character.get_actor_bounds(False, True)
    height = extent.z * 2.0
    if not 80.0 <= height <= 260.0:
        raise RuntimeError(f"unexpected clean-bind character height: {height}")

    camera_location = origin + unreal.Vector(0, 560, 5)
    camera = actors.spawn_actor_from_class(
        unreal.CineCameraActor,
        camera_location,
        unreal.MathLibrary.find_look_at_rotation(camera_location, origin),
    )
    camera.set_actor_label("CAM_HayleyCleanBind_v449")
    camera.camera_component.set_editor_property("current_focal_length", 50.0)
    camera.camera_component.set_editor_property("current_aperture", 5.6)
    for label, offset, intensity in (
        ("KEY", unreal.Vector(-140, 170, 100), 2200.0),
        ("FILL", unreal.Vector(140, 150, 35), 1200.0),
        ("RIM", unreal.Vector(0, -140, 90), 1800.0),
    ):
        light_location = origin + offset
        light = actors.spawn_actor_from_class(
            unreal.RectLight,
            light_location,
            unreal.MathLibrary.find_look_at_rotation(light_location, origin),
        )
        light.set_actor_label(f"{label}_HayleyCleanBind_v449")
        light_component = light.get_component_by_class(unreal.RectLightComponent)
        light_component.set_editor_property("intensity", intensity)
        light_component.set_editor_property("source_width", 100.0)
        light_component.set_editor_property("source_height", 120.0)
    sky = actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector())
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("intensity", 0.8)
    post = actors.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector())
    post.set_editor_property("unbound", True)
    settings = post.get_editor_property("settings")
    settings.set_editor_property("override_auto_exposure_method", True)
    settings.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)
    settings.set_editor_property("override_auto_exposure_bias", True)
    settings.set_editor_property("auto_exposure_bias", 0.8)
    settings.set_editor_property("override_motion_blur_amount", True)
    settings.set_editor_property("motion_blur_amount", 0.0)
    post.set_editor_property("settings", settings)
    if not unreal.EditorLevelLibrary.save_current_level():
        raise RuntimeError("failed to save clean-bind QA map")

    output = OUTPUT / "hayley-clean-bind-front.png"
    started = time.monotonic()
    state = {"warmup": 30, "requested": False}

    def tick(_delta):
        if state["warmup"]:
            state["warmup"] -= 1
            return
        if not state["requested"]:
            state["requested"] = True
            unreal.AutomationLibrary.take_high_res_screenshot(1200, 1600, str(output), camera)
            return
        if output.is_file() and output.stat().st_size > 24:
            report = {
                "schemaVersion": 1,
                "iteration": ITERATION,
                "status": "captured-draft-bind-pose-visual-review-required",
                "map": MAP,
                "mesh": MESH,
                "heightCm": height,
                "frame": {
                    "file": str(output),
                    "bytes": output.stat().st_size,
                    "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                },
                "humanApproved": False,
                "releaseEligible": False,
            }
            (OUTPUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
            unreal.unregister_slate_post_tick_callback(state["handle"])
            unreal.log("HAYLEY_CLEAN_BIND_CAPTURE=" + json.dumps(report, sort_keys=True))
            unreal.SystemLibrary.quit_editor()
        elif time.monotonic() - started > 180:
            raise RuntimeError("clean-bind screenshot timed out")

    state["handle"] = unreal.register_slate_post_tick_callback(tick)
    return state


DRIVER = capture_hayley_clean_bind_v449()
