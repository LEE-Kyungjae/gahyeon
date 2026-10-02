"""Capture all six UE world axes around the unrotated v153 imported head."""

import hashlib
import json
from pathlib import Path
import time

import unreal


MAP = "/Game/Gahyeon/CharacterPipeline/v153/Preview/L_CustomHeadConformSmoke_v153"
LABEL = "CustomHeadTarget_v153"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v155-ue-import-axis-probe"
)
VIEWS = (
    ("plus-x", unreal.Vector(1.0, 0.0, 0.0)),
    ("minus-x", unreal.Vector(-1.0, 0.0, 0.0)),
    ("plus-y", unreal.Vector(0.0, 1.0, 0.0)),
    ("minus-y", unreal.Vector(0.0, -1.0, 0.0)),
    ("plus-z", unreal.Vector(0.0, 0.0, 1.0)),
    ("minus-z", unreal.Vector(0.0, 0.0, -1.0)),
)
_axis_probe_v155 = None


class AxisProbeDriverV155:
    def __init__(self):
        if OUTPUT.exists():
            raise RuntimeError(f"refusing to overwrite v155 axis probe: {OUTPUT}")
        if unreal.EditorLoadingAndSavingUtils.load_map(MAP) is None:
            raise RuntimeError(f"failed to load v153 map: {MAP}")
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        self.target = next((actor for actor in actors.get_all_level_actors()
                            if actor.get_actor_label() == LABEL), None)
        if self.target is None:
            raise RuntimeError(f"v153 target actor unavailable: {LABEL}")
        self.origin, self.extent = self.target.get_actor_bounds(False, True)
        self.distance = max(self.extent.x, self.extent.y, self.extent.z) * 3.2
        self.camera = actors.spawn_actor_from_class(unreal.CameraActor, self.origin, unreal.Rotator())
        self.camera.camera_component.set_editor_property("field_of_view", 40.0)
        OUTPUT.mkdir(parents=True, exist_ok=False)
        self.index = 0
        self.warmup = 90
        self.started = None
        self.records = []
        unreal.EditorPythonScripting.set_keep_python_script_alive(True)
        self.handle = unreal.register_slate_post_tick_callback(self.tick)
        self.prepare()

    def prepare(self):
        name, axis = VIEWS[self.index]
        location = self.origin + axis * self.distance
        self.camera.set_actor_location(location, False, False)
        rotation = unreal.MathLibrary.find_look_at_rotation(location, self.origin)
        self.camera.set_actor_rotation(rotation, False)
        self.current = {"view": name, "axis": [axis.x, axis.y, axis.z],
                        "location": [location.x, location.y, location.z],
                        "rotation": [rotation.pitch, rotation.yaw, rotation.roll],
                        "file": str(OUTPUT / f"{name}.png")}
        self.warmup = 90
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
        if image.is_file() and image.stat().st_size > 1024:
            self.current["sha256"] = hashlib.sha256(image.read_bytes()).hexdigest()
            self.current["bytes"] = image.stat().st_size
            self.records.append(self.current)
            self.index += 1
            if self.index < len(VIEWS):
                self.prepare()
                return
            self.finish()
        elif time.monotonic() - self.started > 120:
            raise RuntimeError(f"v155 capture timed out: {image}")

    def finish(self):
        (OUTPUT / "axis-probe.json").write_text(json.dumps({
            "schemaVersion": 1,
            "iteration": "v155",
            "state": "captured-import-axis-probe",
            "sourceMap": MAP,
            "sourceActor": LABEL,
            "origin": [self.origin.x, self.origin.y, self.origin.z],
            "extent": [self.extent.x, self.extent.y, self.extent.z],
            "views": self.records,
            "identityCandidate": False,
            "automaticApproval": False,
            "productionReady": False
        }, indent=2) + "\n", encoding="utf-8")
        unreal.unregister_slate_post_tick_callback(self.handle)
        unreal.EditorPythonScripting.set_keep_python_script_alive(False)
        unreal.SystemLibrary.quit_editor()


def start_axis_probe_v155():
    global _axis_probe_v155
    _axis_probe_v155 = AxisProbeDriverV155()


start_axis_probe_v155()
