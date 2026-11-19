"""Capture immutable fixed-camera QA of the v169 FaceBuilder MetaHuman assembly."""

import hashlib
import json
import time
from pathlib import Path

import unreal


MAP = "/Game/Gahyeon/CharacterPipeline/v171/Preview/L_FaceBuilderMediumQA_v171"
LABEL = "Gahyeon_FaceBuilderMedium_v169"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v171-metahuman-facebuilder-fixed-camera-qa/renders"
)
VIEWS = (
    ("face-front", 0.0, 170.0, 0.82, 55.0),
    ("face-left45", -120.2, 120.2, 0.82, 55.0),
    ("face-right45", 120.2, 120.2, 0.82, 55.0),
    ("face-left90", -170.0, 0.0, 0.82, 55.0),
    ("face-right90", 170.0, 0.0, 0.82, 55.0),
    ("bust-front", 0.0, 280.0, 0.67, 55.0),
    ("full-body-front", 0.0, 480.0, 0.50, 55.0),
)
_driver_v171 = None


class GahyeonFaceBuilderFixedCameraQaV171:
    def __init__(self):
        if OUTPUT.exists():
            raise RuntimeError(f"refusing to overwrite immutable v171 renders: {OUTPUT}")
        unreal.EditorPythonScripting.set_keep_python_script_alive(True)
        if unreal.EditorLoadingAndSavingUtils.load_map(MAP) is None:
            raise RuntimeError(f"failed to load v171 QA map: {MAP}")
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        character = next(
            (actor for actor in actors.get_all_level_actors() if actor.get_actor_label() == LABEL),
            None,
        )
        if character is None:
            raise RuntimeError(f"v169 character unavailable: {LABEL}")
        self.origin, self.extent = character.get_actor_bounds(False, True)
        height = self.extent.z * 2.0
        if not 130.0 <= height <= 260.0:
            raise RuntimeError(f"unexpected character height: {height}")
        self.camera = actors.spawn_actor_from_class(unreal.CineCameraActor, self.origin)
        component = self.camera.get_cine_camera_component()
        component.set_editor_property("current_aperture", 8.0)
        focus = component.get_editor_property("focus_settings")
        focus.set_editor_property("focus_method", unreal.CameraFocusMethod.DISABLE)
        component.set_editor_property("focus_settings", focus)
        OUTPUT.mkdir(parents=True, exist_ok=False)
        self.index = 0
        self.records = []
        self.handle = unreal.register_slate_post_tick_callback(self.tick)
        self.prepare_view()

    def prepare_view(self):
        name, x, y, height_factor, focal_length = VIEWS[self.index]
        target = unreal.Vector(
            self.origin.x,
            self.origin.y,
            self.origin.z + self.extent.z * height_factor,
        )
        location = target + unreal.Vector(x, y, 0.0)
        self.camera.set_actor_location(location, False, False)
        self.camera.set_actor_rotation(
            unreal.MathLibrary.find_look_at_rotation(location, target), False
        )
        self.camera.get_cine_camera_component().set_editor_property(
            "current_focal_length", focal_length
        )
        self.current = {
            "view": name,
            "target": [target.x, target.y, target.z],
            "location": [location.x, location.y, location.z],
            "focalLengthMm": focal_length,
            "file": str(OUTPUT / f"{name}.png"),
        }
        self.warmup = 300 if self.index == 0 else 75
        self.started = None

    def tick(self, _delta):
        if self.warmup:
            self.warmup -= 1
            return
        image = Path(self.current["file"])
        if self.started is None:
            self.started = time.monotonic()
            unreal.AutomationLibrary.take_high_res_screenshot(
                1200, 1200, str(image), self.camera
            )
            return
        if image.is_file() and image.stat().st_size > 24:
            self.current["sha256"] = hashlib.sha256(image.read_bytes()).hexdigest()
            self.current["sizeBytes"] = image.stat().st_size
            self.records.append(self.current)
            self.index += 1
            if self.index < len(VIEWS):
                self.prepare_view()
                return
            self.finish()
        elif time.monotonic() - self.started > 180:
            unreal.unregister_slate_post_tick_callback(self.handle)
            unreal.EditorPythonScripting.set_keep_python_script_alive(False)
            raise RuntimeError(f"v171 capture timed out: {image}")

    def finish(self):
        (OUTPUT.parent / "capture-report.json").write_text(json.dumps({
            "schemaVersion": 1,
            "iteration": "v171",
            "state": "captured-draft-facebuilder-metahuman-seven-view",
            "engine": "5.8",
            "hypothesis": (
                "The coherent four-view FaceBuilder solve survives MetaHuman conform, "
                "cloud rig enrichment, and Medium runtime assembly without scale or anatomy collapse."
            ),
            "sourceAssembly": "v169",
            "sourceMap": MAP,
            "views": self.records,
            "automaticApproval": False,
            "productionReady": False,
        }, indent=2) + "\n", encoding="utf-8")
        unreal.unregister_slate_post_tick_callback(self.handle)
        unreal.EditorPythonScripting.set_keep_python_script_alive(False)
        unreal.SystemLibrary.quit_editor()


def capture_facebuilder_medium_qa_v171():
    global _driver_v171
    _driver_v171 = GahyeonFaceBuilderFixedCameraQaV171()


capture_facebuilder_medium_qa_v171()
