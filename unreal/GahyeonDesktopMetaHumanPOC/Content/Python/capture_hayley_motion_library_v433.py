"""Recapture Hayley motions after allowing each frozen pose to evaluate."""

import hashlib
import json
from pathlib import Path
import time

import unreal


MAP = "/Game/LivingCharacterPOC/v431/QA/L_HayleyMotionLibrary_v431"
ANIMATIONS = (
    ("idle", "/Game/LivingCharacterPOC/v428/Animation/AS_Hayley_CyberIdle_v428"),
    ("explain", "/Game/LivingCharacterPOC/v429/Animation/AS_Hayley_HandsForward_v429"),
    ("stand-sit", "/Game/LivingCharacterPOC/v430/Animation/AS_Hayley_StandSit_v430"),
)
OUTPUT = Path("/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v433-hayley-motion-library-evaluated")
_driver = None


class EvaluatedMotionDriverV433:
    def __init__(self):
        if OUTPUT.exists():
            raise RuntimeError(f"refusing to overwrite immutable v433 evidence: {OUTPUT}")
        OUTPUT.mkdir(parents=True)
        if not unreal.EditorLevelLibrary.load_level(MAP):
            raise RuntimeError(f"failed to load QA map: {MAP}")
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
        phase_actors = sorted(
            [actor for actor in actors if actor.get_actor_label().startswith("Hayley_MotionPhase_")],
            key=lambda actor: actor.get_actor_label(),
        )
        self.components = [actor.get_component_by_class(unreal.SkeletalMeshComponent) for actor in phase_actors]
        cameras = [actor for actor in actors if isinstance(actor, unreal.CineCameraActor)]
        if len(self.components) != 3 or len(cameras) != 1:
            raise RuntimeError(f"unexpected v431 scene: components={len(self.components)}, cameras={len(cameras)}")
        self.camera = cameras[0]
        self.animations = [(label, path, unreal.load_asset(path)) for label, path in ANIMATIONS]
        if any(asset is None for _, _, asset in self.animations):
            raise RuntimeError("one or more retargeted animations are unavailable")
        self.index = 0
        self.wait_ticks = 30
        self.state = "configure"
        self.started = time.monotonic()
        self.records = []
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def configure(self):
        label, path, animation = self.animations[self.index]
        duration = float(animation.get_play_length())
        phases = (duration * 0.1, duration * 0.5, duration * 0.9)
        for component, phase in zip(self.components, phases):
            component.set_editor_property("global_anim_rate_scale", 1.0)
            component.play_animation(animation, True)
            component.set_position(phase, False)
            component.set_editor_property("global_anim_rate_scale", 0.0)
        self.current = (label, path, duration, phases, OUTPUT / f"hayley-{label}-phases.png")
        self.wait_ticks = 24
        self.state = "warmup"

    def tick(self, _delta):
        if self.state == "configure":
            self.configure()
            return
        if self.state == "warmup":
            self.wait_ticks -= 1
            if self.wait_ticks > 0:
                return
            unreal.AutomationLibrary.take_high_res_screenshot(1920, 1080, str(self.current[4]), self.camera)
            self.state = "await-capture"
            return
        output = self.current[4]
        if output.is_file() and output.stat().st_size > 24:
            label, path, duration, phases, _ = self.current
            self.records.append({
                "label": label, "animation": path, "durationSeconds": duration,
                "phasesSeconds": phases, "file": str(output), "bytes": output.stat().st_size,
                "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            })
            self.index += 1
            if self.index < len(self.animations):
                self.state = "configure"
                return
            report = {
                "schemaVersion": 1, "iteration": "v433",
                "status": "captured-draft-evaluated-hayley-motion-library",
                "sourceMap": MAP, "captures": self.records,
                "captureFix": "Animation is configured once, then evaluated for 24 Slate ticks before capture.",
                "visualValidationPending": True, "humanApproved": False, "releaseEligible": False,
            }
            (OUTPUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
            unreal.unregister_slate_post_tick_callback(self.handle)
            unreal.EditorPythonScripting.set_keep_python_script_alive(False)
            unreal.SystemLibrary.quit_editor()
        elif time.monotonic() - self.started > 240:
            raise RuntimeError(f"v433 capture timed out: {output}")


def capture_hayley_motion_library_v433():
    global _driver
    if _driver is not None:
        raise RuntimeError("v433 capture already running")
    unreal.EditorPythonScripting.set_keep_python_script_alive(True)
    _driver = EvaluatedMotionDriverV433()


capture_hayley_motion_library_v433()
