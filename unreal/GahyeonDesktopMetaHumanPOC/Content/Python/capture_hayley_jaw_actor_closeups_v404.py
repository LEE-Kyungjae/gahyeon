"""Capture close-ups from the independently posed actors in the v402 QA map."""

import hashlib
import json
from pathlib import Path
import time

import unreal


MAP = "/Game/LivingCharacterPOC/v402/QA/L_HayleyJawContactSheet_v402"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v404-hayley-jaw-actor-closeups"
)
LABELS = (
    "neutral",
    "x-plus",
    "x-minus",
    "y-plus",
    "y-minus",
    "z-plus",
    "z-minus",
)
_driver = None


def find_actor_v404(actors, label):
    matches = [actor for actor in actors.get_all_level_actors() if actor.get_actor_label() == label]
    if len(matches) != 1:
        raise RuntimeError(f"expected one actor named {label}, got {len(matches)}")
    return matches[0]


class HayleyJawActorCloseupDriverV404:
    def __init__(self):
        if OUTPUT.exists():
            raise RuntimeError("refusing to overwrite immutable v404 evidence")
        unreal.EditorPythonScripting.set_keep_python_script_alive(True)
        OUTPUT.mkdir(parents=True)
        level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        if not level.load_level(MAP):
            raise RuntimeError(f"failed to load v402 map: {MAP}")
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        self.characters = [
            find_actor_v404(actors, f"Hayley_Jaw_{label}_v402") for label in LABELS
        ]
        self.camera = actors.spawn_actor_from_class(unreal.CineCameraActor, unreal.Vector())
        self.camera.camera_component.set_editor_property("current_focal_length", 70.0)
        self.camera.camera_component.set_editor_property("current_aperture", 8.0)
        self.index = 0
        self.output = None
        self.settle = 0
        self.requested = False
        self.records = []
        self.started = time.monotonic()
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def tick(self, _delta):
        if self.index >= len(self.characters):
            report = {
                "schemaVersion": 1,
                "iteration": "v404",
                "status": "captured-draft-independent-jaw-actor-closeups",
                "sourceMap": MAP,
                "frames": self.records,
                "axisSelectionPending": True,
                "humanApproved": False,
                "releaseEligible": False,
            }
            (OUTPUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
            unreal.unregister_slate_post_tick_callback(self.handle)
            unreal.EditorPythonScripting.set_keep_python_script_alive(False)
            unreal.log("HAYLEY_V404_JAW_CLOSEUPS=" + json.dumps(report, sort_keys=True))
            unreal.SystemLibrary.quit_editor()
            return
        label = LABELS[self.index]
        actor = self.characters[self.index]
        if self.output is None:
            origin, extent = actor.get_actor_bounds(False, True)
            target = unreal.Vector(origin.x, origin.y, origin.z + extent.z * 0.84)
            location = target + unreal.Vector(0.0, 165.0, 0.0)
            self.camera.set_actor_location(location, False, False)
            self.camera.set_actor_rotation(
                unreal.MathLibrary.find_look_at_rotation(location, target), False
            )
            self.output = OUTPUT / f"{self.index:02d}-{label}.png"
            self.settle = 10
            self.requested = False
            return
        if self.settle:
            self.settle -= 1
            return
        if not self.requested:
            self.requested = True
            unreal.AutomationLibrary.take_high_res_screenshot(
                1200, 1200, str(self.output), self.camera
            )
            return
        if self.output.is_file() and self.output.stat().st_size > 24:
            self.records.append({
                "label": label,
                "file": str(self.output),
                "sha256": hashlib.sha256(self.output.read_bytes()).hexdigest(),
            })
            self.index += 1
            self.output = None
        elif time.monotonic() - self.started > 240:
            unreal.EditorPythonScripting.set_keep_python_script_alive(False)
            raise RuntimeError("v404 close-up capture timed out")


def capture_hayley_jaw_actor_closeups_v404():
    global _driver
    if _driver is not None:
        raise RuntimeError("v404 capture already running")
    _driver = HayleyJawActorCloseupDriverV404()


capture_hayley_jaw_actor_closeups_v404()
