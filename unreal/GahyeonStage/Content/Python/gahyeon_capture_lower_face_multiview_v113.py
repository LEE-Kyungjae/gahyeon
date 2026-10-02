"""Capture immutable fixed-camera QA for the v111b lower-face MetaHuman assembly."""

import hashlib
import json
import time
from pathlib import Path

import unreal


MAP = "/Game/Gahyeon/CharacterPipeline/v112/Preview/L_Gahyeon_LowerFace_v112"
LABEL = "Gahyeon_LowerFaceHigh_v111b"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v113-metahuman-lower-face-multiview"
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
_driver = None


class Driver:
    def __init__(self):
        if OUTPUT.exists():
            raise RuntimeError(f"refusing to overwrite immutable v113 capture: {OUTPUT}")
        if unreal.EditorLoadingAndSavingUtils.load_map(MAP) is None:
            raise RuntimeError(f"failed to load v112 map: {MAP}")
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        character = next((actor for actor in actors.get_all_level_actors() if actor.get_actor_label() == LABEL), None)
        if character is None:
            raise RuntimeError(f"v111b High character unavailable: {LABEL}")
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
        self.warmup = 240
        self.started = None
        self.records = []
        self.handle = unreal.register_slate_post_tick_callback(self.tick)
        self.prepare_view()

    def prepare_view(self):
        name, offset, height_factor, focal_length = VIEWS[self.index]
        target = unreal.Vector(
            self.origin.x,
            self.origin.y,
            self.origin.z + self.extent.z * height_factor,
        )
        location = target + unreal.Vector(offset[0], offset[1], 0.0)
        self.camera.set_actor_location(location, False, False)
        self.camera.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(location, target), False)
        self.camera.get_cine_camera_component().set_editor_property("current_focal_length", focal_length)
        self.current = {
            "view": name,
            "target": [target.x, target.y, target.z],
            "location": [location.x, location.y, location.z],
            "focalLengthMm": focal_length,
            "file": str(OUTPUT / f"{name}.png"),
        }
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
            raise RuntimeError(f"v113 capture timed out: {image}")

    def finish(self):
        report = OUTPUT / "capture-report.json"
        report.write_text(json.dumps({
            "schemaVersion": 1,
            "iteration": "v113",
            "state": "captured-draft-lower-face-multiview",
            "engine": "5.8",
            "hypothesis": "The constrained v109b native sculpt shortens the lower face while preserving v106 facial widths and functional Mac Groom presentation.",
            "baseline": "v106",
            "sourceAssembly": "v111b",
            "sourcePreview": "v112",
            "map": MAP,
            "characterBounds": {
                "origin": [self.origin.x, self.origin.y, self.origin.z],
                "extent": [self.extent.x, self.extent.y, self.extent.z],
            },
            "views": self.records,
            "faceCameraContractMatchesV106": True,
            "fullBodyDistanceCm": 760.0,
            "manualGroomOffset": False,
            "automaticApproval": False,
            "productionReady": False,
        }, indent=2) + "\n", encoding="utf-8")
        unreal.unregister_slate_post_tick_callback(self.handle)
        unreal.SystemLibrary.quit_editor()


def capture_lower_face_multiview_v113():
    global _driver
    _driver = Driver()


capture_lower_face_multiview_v113()
