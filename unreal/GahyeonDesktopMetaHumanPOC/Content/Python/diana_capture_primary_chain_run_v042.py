"""Capture fixed editor renders of Diana's primary-chain run candidate."""

import hashlib
import json
import time
from pathlib import Path

import unreal


MAP = "/Game/Gahyeon/Character2/Diana/v041/QA/L_Diana_PrimaryChainRun_v041"
CHARACTER_LABEL = "Diana_v041_PrimaryChainRunDraft"
CAMERA_LABEL = "CAM_Diana_FullBody_v041"
ANIMATION = (
    "/Game/Gahyeon/Character2/Diana/v040/Animation/"
    "AS_Diana_RunForward_v244_PrimaryLegs_v040"
)
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v044-diana-primary-chain-run-qa"
)
SAMPLE_SECONDS = (0.28,)
_driver = None


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Driver:
    def __init__(self):
        if OUTPUT.exists():
            raise RuntimeError(f"refusing to overwrite immutable iteration: {OUTPUT}")
        (OUTPUT / "frames").mkdir(parents=True)
        if unreal.EditorLoadingAndSavingUtils.load_map(MAP) is None:
            raise RuntimeError(f"failed to load map: {MAP}")
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        self.character = next(
            (actor for actor in actors.get_all_level_actors()
             if actor.get_actor_label() == CHARACTER_LABEL),
            None,
        )
        self.camera = next(
            (actor for actor in actors.get_all_level_actors()
             if actor.get_actor_label() == CAMERA_LABEL),
            None,
        )
        if self.character is None or self.camera is None:
            raise RuntimeError("v041 character or fixed camera unavailable")
        self.component = self.character.get_component_by_class(unreal.SkeletalMeshComponent)
        self.animation = unreal.EditorAssetLibrary.load_asset(ANIMATION)
        if self.component is None or self.animation is None:
            raise RuntimeError("v041 skeletal component or v040 animation unavailable")
        self.component.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
        self.component.play_animation(self.animation, False)
        self.queue = list(SAMPLE_SECONDS)
        self.pending = None
        self.settling = None
        self.records = []
        self.warmup = 10
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def set_pose(self, seconds):
        self.component.set_position(seconds, False)
        self.component.tick_animation(0.0, False)
        self.component.refresh_bone_transforms()

    def tick(self, _delta):
        if self.warmup:
            self.warmup -= 1
            return
        if self.pending is not None:
            seconds, path, started = self.pending
            if path.is_file() and path.stat().st_size > 24:
                self.records.append({
                    "timeSeconds": seconds,
                    "file": str(path),
                    "sha256": sha256(path),
                    "sizeBytes": path.stat().st_size,
                })
                self.pending = None
                self.warmup = 20
            elif time.monotonic() - started > 120:
                raise RuntimeError(f"capture timed out: {path}")
            return
        if self.settling is not None:
            seconds, remaining = self.settling
            self.set_pose(seconds)
            if remaining > 0:
                self.settling = (seconds, remaining - 1)
                return
            path = OUTPUT / "frames" / f"run-{seconds:04.2f}s.png"
            self.pending = (seconds, path, time.monotonic())
            self.settling = None
            unreal.AutomationLibrary.take_high_res_screenshot(
                1600, 1200, str(path), self.camera
            )
            return
        if self.queue:
            seconds = self.queue.pop(0)
            self.set_pose(seconds)
            self.settling = (seconds, 12)
            return

        report = {
            "schemaVersion": 1,
            "iteration": "v044",
            "status": "captured-draft-primary-chain-run",
            "hypothesis": (
                "Removing duplicate auxiliary-leg retarget mappings prevents the "
                "NeoJacket2 and waist pieces from receiving a second leg motion."
            ),
            "map": MAP,
            "animation": ANIMATION,
            "frames": self.records,
            "uniqueFrameHashes": len({record["sha256"] for record in self.records}),
            "visualValidationPending": True,
            "humanApproved": False,
            "automaticApproval": False,
        }
        (OUTPUT / "capture-report.json").write_text(
            json.dumps(report, indent=2) + "\n"
        )
        unreal.unregister_slate_post_tick_callback(self.handle)
        unreal.log("Diana v044 primary-chain capture completed")
        unreal.SystemLibrary.quit_editor()


def main():
    global _driver
    if _driver is not None:
        raise RuntimeError("Diana v042 capture already running")
    _driver = Driver()


main()
