"""Capture one fixed-camera representative phase for Diana's v427 motion library."""

import hashlib
import json
from pathlib import Path
import time

import unreal


MAP = "/Game/Gahyeon/Character2/Diana/v421/Runtime/L_DianaMacRuntimeAttachmentGravity_v421"
MOTIONS = (
    ("active-idle", "/Game/Gahyeon/Character2/Diana/v427/Animation/AS_Diana_ActiveIdle_ComponentCopy_v427", 0.35),
    ("walk-alt", "/Game/Gahyeon/Character2/Diana/v427/Animation/AS_Diana_WalkAlt_ComponentCopy_v427", 0.50),
    ("explain", "/Game/Gahyeon/Character2/Diana/v427/Animation/AS_Diana_Explain_ComponentCopy_v427", 0.50),
    ("stand-sit", "/Game/Gahyeon/Character2/Diana/v427/Animation/AS_Diana_StandSit_ComponentCopy_v427", 0.50),
    ("narration", "/Game/Gahyeon/Character2/Diana/v427/Animation/AS_Diana_Narration_ComponentCopy_v427", 0.50),
)
OUTPUT = Path("/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/v430-diana-motion-library-qa")
_driver = None


class Driver:
    def __init__(self):
        if OUTPUT.exists():
            raise RuntimeError(f"refusing to overwrite immutable QA: {OUTPUT}")
        (OUTPUT / "frames").mkdir(parents=True)
        if unreal.EditorLoadingAndSavingUtils.load_map(MAP) is None:
            raise RuntimeError(f"failed to load fixed-camera map: {MAP}")
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
        characters = [actor for actor in actors if isinstance(actor, unreal.SkeletalMeshActor)]
        cameras = [actor for actor in actors if isinstance(actor, unreal.CameraActor)]
        if len(characters) != 1 or not cameras:
            raise RuntimeError(f"expected one character and a camera, got {len(characters)}, {len(cameras)}")
        self.component = characters[0].get_component_by_class(unreal.SkeletalMeshComponent)
        self.camera = cameras[0]
        self.queue = list(MOTIONS)
        self.pending = None
        self.settling = None
        self.records = []
        self.warmup = 30
        self.started = time.monotonic()
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def pose(self, animation, seconds):
        self.component.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
        self.component.play_animation(animation, False)
        self.component.set_position(seconds, False)
        self.component.set_editor_property("global_anim_rate_scale", 0.0)

    def tick(self, _delta):
        if self.warmup:
            self.warmup -= 1
            return
        if self.pending:
            label, animation_path, fraction, seconds, path = self.pending
            if path.is_file() and path.stat().st_size > 24:
                self.records.append({
                    "label": label,
                    "animation": animation_path,
                    "phaseFraction": fraction,
                    "timeSeconds": seconds,
                    "file": str(path),
                    "bytes": path.stat().st_size,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                })
                self.pending = None
                self.warmup = 15
            elif time.monotonic() - self.started > 240:
                raise RuntimeError(f"capture timed out: {path}")
            return
        if self.settling:
            label, animation_path, fraction, animation, seconds, remaining = self.settling
            self.pose(animation, seconds)
            if remaining:
                self.settling = (label, animation_path, fraction, animation, seconds, remaining - 1)
                return
            path = OUTPUT / "frames" / f"{label}.png"
            self.pending = (label, animation_path, fraction, seconds, path)
            self.settling = None
            unreal.AutomationLibrary.take_high_res_screenshot(1600, 1258, str(path), self.camera)
            return
        if self.queue:
            label, animation_path, fraction = self.queue.pop(0)
            animation = unreal.load_asset(animation_path)
            if animation is None:
                raise RuntimeError(f"missing motion: {animation_path}")
            seconds = float(animation.get_play_length()) * fraction
            self.pose(animation, seconds)
            self.settling = (label, animation_path, fraction, animation, seconds, 12)
            return
        report = {
            "schemaVersion": 1,
            "iteration": "v430",
            "status": "captured-draft-motion-library",
            "map": MAP,
            "frames": self.records,
            "licenseStatus": "blocked-missing-source-url-and-commercial-redistribution-license",
            "visualValidationPending": True,
            "humanApproved": False,
            "releaseEligible": False,
        }
        (OUTPUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        unreal.unregister_slate_post_tick_callback(self.handle)
        unreal.EditorPythonScripting.set_keep_python_script_alive(False)
        unreal.SystemLibrary.quit_editor()


def main():
    global _driver
    unreal.EditorPythonScripting.set_keep_python_script_alive(True)
    _driver = Driver()


main()
