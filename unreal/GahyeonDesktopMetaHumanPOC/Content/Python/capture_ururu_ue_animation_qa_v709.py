"""Render fixed-camera evidence from Ururu's imported UE facial AnimSequence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
MESH_PATH = "/Game/LivingCharacterPOC/v693/Characters/UruruFacial/Ururu_StaticHeadMorphs_v691"
ANIMATION_PATH = "/Game/LivingCharacterPOC/v708/Animation/UruruFace/Ururu_HeadMorphs_Centimeter_v688"
DONOR_PATH = "/Game/LivingCharacterPOC/v585/Characters/UruruCentimeterNormalized/Ururu_CentimeterNormalized_v584"
MAP_PATH = "/Game/LivingCharacterPOC/v709/QA/L_UruruFaceAnimationQA_v709"
OUTPUT = ROOT / "artifacts/living-character-poc-v709-ururu-ue-face-animation-qa"
FPS = 24.0
STATES = (("neutral", 1), ("blink", 10), ("gaze-left", 20), ("gaze-right", 30))
MORPHS = ("EyeBlink_L", "EyeBlink_R", "GazeLeft", "GazeRight")
_driver = None


class UruruFaceAnimationCaptureV709:
    def __init__(self) -> None:
        if OUTPUT.exists() or unreal.EditorAssetLibrary.does_asset_exist(MAP_PATH):
            raise RuntimeError("refusing to overwrite immutable v709 evidence")
        mesh = unreal.load_asset(MESH_PATH)
        animation = unreal.load_asset(ANIMATION_PATH)
        donor = unreal.load_asset(DONOR_PATH)
        if not isinstance(mesh, unreal.SkeletalMesh):
            raise RuntimeError("v709 facial mesh is unavailable")
        if not isinstance(animation, unreal.AnimSequence):
            raise RuntimeError("v709 facial AnimSequence is unavailable")
        if not isinstance(donor, unreal.SkeletalMesh):
            raise RuntimeError("v709 validated material donor is unavailable")
        if mesh.get_editor_property("skeleton") != animation.get_editor_property("skeleton"):
            raise RuntimeError("v709 mesh and animation skeletons differ")
        if not set(MORPHS).issubset(set(str(name) for name in mesh.get_all_morph_target_names())):
            raise RuntimeError("v709 facial mesh lacks required morph targets")

        OUTPUT.mkdir(parents=True, exist_ok=False)
        if not unreal.EditorLevelLibrary.new_level(MAP_PATH):
            raise RuntimeError("failed to create v709 QA map")
        subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        actor = subsystem.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(), unreal.Rotator())
        actor.set_actor_label("UruruFaceAnimationQA_v709")
        self.component = actor.get_component_by_class(unreal.SkeletalMeshComponent)
        self.component.set_editor_property("skeletal_mesh_asset", mesh)
        self.component.set_update_animation_in_editor(True)
        self.animation = animation

        donor_materials = {
            str(slot.material_slot_name): slot.material_interface
            for slot in donor.get_editor_property("materials")
            if slot.material_interface is not None
        }
        self.borrowed = []
        for index, slot in enumerate(mesh.get_editor_property("materials")):
            name = str(slot.material_slot_name)
            material = donor_materials.get(name)
            if material is not None:
                self.component.set_material(index, material)
                self.borrowed.append({"slot": index, "name": name, "material": material.get_path_name()})
        if len(self.borrowed) < 9:
            raise RuntimeError(f"too few restored material slots: {self.borrowed}")

        origin, extent = actor.get_actor_bounds(False, True)
        height = extent.z * 2.0
        if not 130.0 <= height <= 190.0:
            raise RuntimeError(f"implausible v709 character height: {height}")
        target = unreal.Vector(origin.x, origin.y, origin.z + extent.z * 0.72)
        camera_location = target + unreal.Vector(0.0, 155.0, 0.0)
        self.camera = subsystem.spawn_actor_from_class(
            unreal.CineCameraActor,
            camera_location,
            unreal.MathLibrary.find_look_at_rotation(camera_location, target),
        )
        camera = self.camera.get_cine_camera_component()
        camera.set_editor_property("current_focal_length", 55.0)
        camera.set_editor_property("current_aperture", 8.0)
        focus = camera.get_editor_property("focus_settings")
        focus.set_editor_property("focus_method", unreal.CameraFocusMethod.DISABLE)
        camera.set_editor_property("focus_settings", focus)
        for offset, intensity in (
            (unreal.Vector(-85.0, 110.0, 45.0), 2600.0),
            (unreal.Vector(85.0, 100.0, 20.0), 1500.0),
            (unreal.Vector(0.0, -90.0, 55.0), 2000.0),
        ):
            location = target + offset
            light = subsystem.spawn_actor_from_class(
                unreal.RectLight, location, unreal.MathLibrary.find_look_at_rotation(location, target)
            )
            light_component = light.get_component_by_class(unreal.RectLightComponent)
            light_component.set_editor_property("intensity", intensity)
            light_component.set_editor_property("source_width", 90.0)
            light_component.set_editor_property("source_height", 90.0)
        sky = subsystem.spawn_actor_from_class(unreal.SkyLight, unreal.Vector())
        sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("intensity", 0.7)
        post = subsystem.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector())
        post.set_editor_property("unbound", True)
        settings = post.get_editor_property("settings")
        settings.set_editor_property("override_auto_exposure_method", True)
        settings.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)
        settings.set_editor_property("override_auto_exposure_bias", True)
        settings.set_editor_property("auto_exposure_bias", 0.0)
        settings.set_editor_property("override_motion_blur_amount", True)
        settings.set_editor_property("motion_blur_amount", 0.0)
        post.set_editor_property("settings", settings)
        if not unreal.EditorLevelLibrary.save_current_level():
            raise RuntimeError("failed to save v709 QA map")

        self.index = 0
        self.current = None
        self.requested = False
        self.warmup = 300
        self.state_warmup = 0
        self.started = time.monotonic()
        self.frames = []
        unreal.EditorPythonScripting.set_keep_python_script_alive(True)
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def finish(self) -> None:
        hashes = [frame["sha256"] for frame in self.frames]
        if len(set(hashes)) != len(hashes):
            raise RuntimeError(f"v709 animation states produced duplicate render bytes: {hashes}")
        report = {
            "schemaVersion": 1,
            "iteration": "v709",
            "status": "captured-draft-ue-facial-animation-evidence",
            "mesh": MESH_PATH,
            "animation": ANIMATION_PATH,
            "map": MAP_PATH,
            "materialDonor": DONOR_PATH,
            "borrowedMaterials": self.borrowed,
            "states": self.frames,
            "camera": {"distanceCm": 155.0, "focalLengthMm": 55.0, "exposureBias": 0.0},
            "visualValidationPending": True,
            "automaticApproval": False,
            "humanApproved": False,
            "productionReady": False,
        }
        (OUTPUT / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        unreal.log("URURU_UE_FACE_ANIMATION_QA_V709=" + json.dumps(report, sort_keys=True))
        unreal.unregister_slate_post_tick_callback(self.handle)
        unreal.EditorPythonScripting.set_keep_python_script_alive(False)
        unreal.SystemLibrary.quit_editor()

    def tick(self, _delta: float) -> None:
        if time.monotonic() - self.started > 300:
            raise RuntimeError("v709 facial animation capture timed out")
        if self.warmup:
            self.warmup -= 1
            return
        if self.index >= len(STATES):
            self.finish()
            return
        label, frame = STATES[self.index]
        output = OUTPUT / f"{label}.png"
        if self.current is None:
            position = frame / FPS
            self.component.override_animation_data(self.animation, False, False, position, 0.0)
            self.current = output
            self.requested = False
            self.state_warmup = 40
            return
        if self.state_warmup:
            self.state_warmup -= 1
            return
        if not self.requested:
            self.requested = True
            unreal.AutomationLibrary.take_high_res_screenshot(1200, 1200, str(output), self.camera)
            return
        if output.is_file() and output.stat().st_size > 1024:
            position = STATES[self.index][1] / FPS
            self.frames.append({
                "label": label,
                "sourceFrame": frame,
                "positionSeconds": position,
                "observedMorphWeights": {name: float(self.component.get_morph_target(name)) for name in MORPHS},
                "file": str(output),
                "bytes": output.stat().st_size,
                "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            })
            self.index += 1
            self.current = None
            self.requested = False
            self.warmup = 15


def capture_ururu_ue_animation_qa_v709() -> None:
    global _driver
    _driver = UruruFaceAnimationCaptureV709()


capture_ururu_ue_animation_qa_v709()
