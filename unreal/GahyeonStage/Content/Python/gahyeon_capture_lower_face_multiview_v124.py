"""Capture immutable fixed-camera QA for calibrated v122 High assembly."""

import hashlib
import json
import time
from pathlib import Path

import unreal


MAP = "/Game/Gahyeon/CharacterPipeline/v123/Preview/L_Gahyeon_LowerFace_v123"
LABEL = "Gahyeon_LowerFaceHigh_v122"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v124-metahuman-lower-face-multiview"
)
VIEWS = (
    ("face-front", (0.0, 170.0), 0.82, 55.0),
    ("face-orbit-left45", (-120.2, 120.2), 0.82, 55.0),
    ("face-orbit-right45", (120.2, 120.2), 0.82, 55.0),
    ("face-orbit-left90", (-170.0, 0.0), 0.82, 55.0),
    ("face-orbit-right90", (170.0, 0.0), 0.82, 55.0),
    ("hair-rear", (0.0, -170.0), 0.82, 55.0),
    ("full-front", (0.0, 760.0), 0.50, 50.0),
)
_driver_v124 = None


class CaptureDriverV124:
    def __init__(self):
        if OUTPUT.exists():
            raise RuntimeError(f"refusing to overwrite immutable v124 capture: {OUTPUT}")
        unreal.EditorPythonScripting.set_keep_python_script_alive(True)
        if unreal.EditorLoadingAndSavingUtils.load_map(MAP) is None:
            raise RuntimeError(f"failed to load v123 map: {MAP}")
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        character = next((actor for actor in actors.get_all_level_actors() if actor.get_actor_label() == LABEL), None)
        if character is None:
            raise RuntimeError(f"v122 High character unavailable: {LABEL}")
        self.origin, self.extent = character.get_actor_bounds(False, True)
        if not 130.0 <= self.extent.z * 2.0 <= 260.0:
            raise RuntimeError(f"unexpected character height: {self.extent.z * 2.0}")
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
        name, offset, height_factor, focal_length = VIEWS[self.index]
        target = unreal.Vector(self.origin.x, self.origin.y, self.origin.z + self.extent.z * height_factor)
        location = target + unreal.Vector(offset[0], offset[1], 0.0)
        self.camera.set_actor_location(location, False, False)
        self.camera.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(location, target), False)
        self.camera.get_cine_camera_component().set_editor_property("current_focal_length", focal_length)
        self.current = {"view": name, "target": [target.x, target.y, target.z],
                        "location": [location.x, location.y, location.z],
                        "focalLengthMm": focal_length, "file": str(OUTPUT / f"{name}.png")}
        self.warmup = 240 if self.index == 0 else 60
        self.started = None

    def tick(self, _delta):
        if self.warmup:
            self.warmup -= 1
            return
        image = Path(self.current["file"])
        if self.started is None:
            self.started = time.monotonic()
            unreal.AutomationLibrary.take_high_res_screenshot(1200, 1200, str(image), self.camera)
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
            raise RuntimeError(f"v124 capture timed out: {image}")

    def finish(self):
        (OUTPUT / "capture-report.json").write_text(json.dumps({
            "schemaVersion": 1,
            "iteration": "v124",
            "state": "captured-draft-calibrated-lower-face-multiview",
            "engine": "5.8",
            "hypothesis": "The calibrated v120 native sculpt visibly reduces the lower-face error without degrading the rig, hair presentation, or other facial proportions.",
            "baseline": "v113",
            "sourceAssembly": "v122",
            "sourcePreview": "v123",
            "map": MAP,
            "views": self.records,
            "faceCameraContractMatchesV113": True,
            "manualGroomOffset": False,
            "automaticApproval": False,
            "productionReady": False,
        }, indent=2) + "\n", encoding="utf-8")
        unreal.unregister_slate_post_tick_callback(self.handle)
        unreal.EditorPythonScripting.set_keep_python_script_alive(False)
        unreal.SystemLibrary.quit_editor()


def capture_lower_face_multiview_v124():
    global _driver_v124
    _driver_v124 = CaptureDriverV124()


capture_lower_face_multiview_v124()
