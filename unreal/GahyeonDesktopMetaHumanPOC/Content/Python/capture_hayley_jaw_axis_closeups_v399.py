"""Recapture v398 jaw poses after allowing UE one animation-evaluation tick."""

import hashlib
import json
from pathlib import Path
import time

import unreal


MAP = "/Game/LivingCharacterPOC/v398/QA/L_HayleyJawAxisCloseups_v398"
ANIMATION = "/Game/LivingCharacterPOC/v391/JawAxisSweepImport/Hayley_JawAxisSweep_Full_v390_Anim"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/"
    "living-character-poc-v399-hayley-jaw-axis-closeups"
)
POSES = (
    ("neutral", 0.0),
    ("jaw-x-plus-5", 0.3),
    ("jaw-x-minus-5", 0.633333),
    ("jaw-y-plus-5", 0.966667),
    ("jaw-y-minus-5", 1.3),
    ("jaw-z-plus-5", 1.633333),
    ("jaw-z-minus-5", 1.966667),
)
_driver = None


def find_actor_v399(actors, label):
    matches = [actor for actor in actors.get_all_level_actors() if actor.get_actor_label() == label]
    if len(matches) != 1:
        raise RuntimeError(f"expected one {label} actor, got {len(matches)}")
    return matches[0]


class JawAxisCaptureDriverV399:
    def __init__(self):
        if OUTPUT.exists():
            raise RuntimeError("refusing to overwrite immutable v399 evidence")
        OUTPUT.mkdir(parents=True)
        level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        if not level.load_level(MAP):
            raise RuntimeError(f"failed to load calibration map: {MAP}")
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        actor = find_actor_v399(actors, "Hayley_JawAxisSweep_v398")
        self.camera = find_actor_v399(actors, "CAM_HayleyJawAxis_v398")
        self.component = actor.get_component_by_class(unreal.SkeletalMeshComponent)
        animation = unreal.load_asset(ANIMATION)
        if animation is None:
            raise RuntimeError(f"missing calibration animation: {ANIMATION}")
        self.component.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
        self.component.play_animation(animation, True)
        self.index = 0
        self.phase = "position"
        self.current_output = None
        self.settle = 0
        self.records = []
        self.started = time.monotonic()
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def finish(self):
        report = {
            "schemaVersion": 1,
            "iteration": "v399",
            "status": "captured-draft-one-tick-evaluated-jaw-axis-closeups",
            "sourceMap": MAP,
            "animation": ANIMATION,
            "frames": self.records,
            "evaluationMethod": "seek-at-rate-one-then-freeze-on-next-slate-tick",
            "axisSelectionPending": True,
            "humanApproved": False,
            "releaseEligible": False,
        }
        (OUTPUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        unreal.unregister_slate_post_tick_callback(self.handle)
        unreal.log("HAYLEY_V399_JAW_CLOSEUPS=" + json.dumps(report, sort_keys=True))
        unreal.SystemLibrary.quit_editor()

    def tick(self, _delta):
        if self.index >= len(POSES):
            self.finish()
            return
        label, position = POSES[self.index]
        if self.phase == "position":
            self.component.set_editor_property("global_anim_rate_scale", 1.0)
            self.component.set_position(position, False)
            self.phase = "freeze"
            return
        if self.phase == "freeze":
            self.component.set_editor_property("global_anim_rate_scale", 0.0)
            self.current_output = OUTPUT / f"{self.index:02d}-{label}.png"
            self.settle = 8
            self.phase = "settle"
            return
        if self.phase == "settle":
            if self.settle:
                self.settle -= 1
                return
            unreal.AutomationLibrary.take_high_res_screenshot(
                1200, 1200, str(self.current_output), self.camera
            )
            self.phase = "wait-file"
            return
        if self.phase == "wait-file":
            if self.current_output.is_file() and self.current_output.stat().st_size > 24:
                self.records.append({
                    "label": label,
                    "requestedPositionSeconds": position,
                    "file": str(self.current_output),
                    "sha256": hashlib.sha256(self.current_output.read_bytes()).hexdigest(),
                })
                self.index += 1
                self.phase = "position"
            elif time.monotonic() - self.started > 240:
                raise RuntimeError("v399 jaw-axis capture timed out")


def capture_hayley_jaw_axis_closeups_v399():
    global _driver
    if _driver is not None:
        raise RuntimeError("v399 capture already running")
    _driver = JawAxisCaptureDriverV399()


capture_hayley_jaw_axis_closeups_v399()
