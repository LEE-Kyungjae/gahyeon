"""Capture fixed-camera UE 5.8 evidence for Ururu's first native face morphs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
MESH_PATH = "/Game/LivingCharacterPOC/v693/Characters/UruruFacial/Ururu_StaticHeadMorphs_v691"
SKELETON_PATH = "/Game/LivingCharacterPOC/v585/Characters/UruruCentimeterNormalized/Ururu_CentimeterNormalized_v584_Skeleton"
MAP = "/Game/LivingCharacterPOC/v695/QA/L_UruruNativeFaceMorphQA_v695"
OUTPUT = ROOT / "artifacts/living-character-poc-v695-ururu-ue-face-morph-qa"
STATES = (
    ("neutral", {}),
    ("blink", {"EyeBlink_L": 1.0, "EyeBlink_R": 1.0}),
    ("blink-left", {"EyeBlink_L": 1.0}),
    ("gaze-left", {"GazeLeft": 1.0}),
    ("gaze-right", {"GazeRight": 1.0}),
)
_driver = None


class UruruFaceMorphCaptureV695:
    def __init__(self):
        if OUTPUT.exists() or unreal.EditorAssetLibrary.does_asset_exist(MAP):
            raise RuntimeError("refusing to overwrite immutable v695 evidence")
        mesh = unreal.load_asset(MESH_PATH)
        skeleton = unreal.load_asset(SKELETON_PATH)
        if not isinstance(mesh, unreal.SkeletalMesh) or skeleton is None:
            raise RuntimeError("v695 dependencies are unavailable")
        if mesh.get_editor_property("skeleton") != skeleton:
            raise RuntimeError("v695 mesh is not bound to the validated v585 skeleton")
        morphs = set(str(name) for name in mesh.get_all_morph_target_names())
        required = {name for _, values in STATES for name in values}
        if not required.issubset(morphs):
            raise RuntimeError(f"missing v695 morphs: {sorted(required - morphs)}")

        OUTPUT.mkdir(parents=True, exist_ok=False)
        if not unreal.EditorLevelLibrary.new_level(MAP):
            raise RuntimeError("failed to create v695 QA map")
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        actor = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(), unreal.Rotator())
        actor.set_actor_label("UruruNativeFaceMorphQA_v695")
        self.component = actor.get_component_by_class(unreal.SkeletalMeshComponent)
        self.component.set_editor_property("skeletal_mesh_asset", mesh)
        self.origin, self.extent = actor.get_actor_bounds(False, True)
        height = self.extent.z * 2.0
        if not 130.0 <= height <= 190.0:
            raise RuntimeError(f"implausible v695 character height: {height}")
        self.target = unreal.Vector(self.origin.x, self.origin.y, self.origin.z + self.extent.z * 0.72)
        camera_location = self.target + unreal.Vector(0.0, 155.0, 0.0)
        self.camera = actors.spawn_actor_from_class(
            unreal.CineCameraActor,
            camera_location,
            unreal.MathLibrary.find_look_at_rotation(camera_location, self.target),
        )
        camera_component = self.camera.get_cine_camera_component()
        camera_component.set_editor_property("current_focal_length", 55.0)
        camera_component.set_editor_property("current_aperture", 8.0)
        focus = camera_component.get_editor_property("focus_settings")
        focus.set_editor_property("focus_method", unreal.CameraFocusMethod.DISABLE)
        camera_component.set_editor_property("focus_settings", focus)
        for offset, intensity in (
            (unreal.Vector(-85.0, 110.0, 45.0), 2600.0),
            (unreal.Vector(85.0, 100.0, 20.0), 1500.0),
            (unreal.Vector(0.0, -90.0, 55.0), 2000.0),
        ):
            location = self.target + offset
            light = actors.spawn_actor_from_class(
                unreal.RectLight, location, unreal.MathLibrary.find_look_at_rotation(location, self.target)
            )
            light_component = light.get_component_by_class(unreal.RectLightComponent)
            light_component.set_editor_property("intensity", intensity)
            light_component.set_editor_property("source_width", 90.0)
            light_component.set_editor_property("source_height", 90.0)
        sky = actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector())
        sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("intensity", 0.7)
        post = actors.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector())
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
            raise RuntimeError("failed to save v695 QA map")

        self.index = 0
        self.current = None
        self.warmup = 180
        self.started = time.monotonic()
        self.frames = []
        unreal.EditorPythonScripting.set_keep_python_script_alive(True)
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def apply_state(self, values):
        self.component.clear_morph_targets()
        for name, value in values.items():
            self.component.set_morph_target(name, value, False)

    def finish(self):
        report = {
            "schemaVersion": 1,
            "iteration": "v695",
            "status": "captured-draft-ue-native-face-morph-evidence",
            "mesh": MESH_PATH,
            "skeleton": SKELETON_PATH,
            "map": MAP,
            "states": self.frames,
            "camera": {"distanceCm": 155.0, "focalLengthMm": 55.0, "exposureBias": 0.0},
            "visualValidationPending": True,
            "automaticApproval": False,
            "humanApproved": False,
            "productionReady": False,
        }
        (OUTPUT / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        unreal.log("URURU_UE_FACE_MORPH_QA_V695=" + json.dumps(report, sort_keys=True))
        unreal.unregister_slate_post_tick_callback(self.handle)
        unreal.EditorPythonScripting.set_keep_python_script_alive(False)
        unreal.SystemLibrary.quit_editor()

    def tick(self, _delta):
        if time.monotonic() - self.started > 240:
            raise RuntimeError("v695 face morph capture timed out")
        if self.warmup:
            self.warmup -= 1
            return
        if self.index >= len(STATES):
            self.finish()
            return
        label, values = STATES[self.index]
        output = OUTPUT / f"{label}.png"
        if self.current is None:
            self.apply_state(values)
            self.current = output
            unreal.AutomationLibrary.take_high_res_screenshot(1200, 1200, str(output), self.camera)
            return
        if output.is_file() and output.stat().st_size > 1024:
            self.frames.append({
                "label": label,
                "morphWeights": values,
                "file": str(output),
                "bytes": output.stat().st_size,
                "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            })
            self.index += 1
            self.current = None
            self.warmup = 12


def capture_ururu_ue_face_morph_qa_v695():
    global _driver
    _driver = UruruFaceMorphCaptureV695()


capture_ururu_ue_face_morph_qa_v695()
