"""Capture fixed-camera v088 facial animation frames without modifying source assets."""

import hashlib
import json
import os
import time
from pathlib import Path

import unreal


MAP = "/Game/Gahyeon/CharacterPipeline/v089/Preview/L_Skotukeda_WardrobeGroom_v089"
CHARACTER_LABEL = "Skotukeda_WardrobeGroomQA_v088"
ANIMATION = "/Game/Gahyeon/TalkingPOC/v092/Animation/AS_GahyeonTalkingFace_v092"
SAMPLE_TIMES = (0.0, 1.5, 3.0, 5.0)
_driver = None


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TalkingPlaybackCaptureV093:
    def __init__(self):
        self.output = Path(os.environ["GAHYEON_TALKING_CAPTURE_ROOT"]).resolve()
        if self.output.exists():
            raise RuntimeError(f"refusing to overwrite v093 capture root: {self.output}")
        (self.output / "frames").mkdir(parents=True)
        if unreal.EditorLoadingAndSavingUtils.load_map(MAP) is None:
            raise RuntimeError(f"failed to load map: {MAP}")
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        matches = [actor for actor in actors.get_all_level_actors()
                   if actor.get_actor_label() == CHARACTER_LABEL]
        if len(matches) != 1:
            raise RuntimeError(f"expected one v088 actor, got {len(matches)}")
        self.character = matches[0]
        faces = [component for component in
                 self.character.get_components_by_class(unreal.SkeletalMeshComponent)
                 if component.get_name() == "Face"]
        if len(faces) != 1:
            names = [component.get_name() for component in
                     self.character.get_components_by_class(unreal.SkeletalMeshComponent)]
            raise RuntimeError(f"expected v088 Face component, got {names}")
        self.face = faces[0]
        self.animation = unreal.load_asset(ANIMATION)
        if self.animation is None:
            raise RuntimeError(f"animation unavailable: {ANIMATION}")
        self.face.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
        self.face.set_animation(self.animation)
        self.face.set_play_rate(0.0)

        origin, extent = self.character.get_actor_bounds(False, True)
        target = unreal.Vector(origin.x, origin.y, origin.z + extent.z * 0.72)
        location = target + unreal.Vector(0.0, 210.0, 0.0)
        self.camera = actors.spawn_actor_from_class(unreal.CineCameraActor, location)
        self.camera.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(location, target), False)
        component = self.camera.get_cine_camera_component()
        component.set_editor_property("current_focal_length", 65.0)
        component.set_editor_property("current_aperture", 8.0)
        focus = component.get_editor_property("focus_settings")
        focus.set_editor_property("focus_method", unreal.CameraFocusMethod.DISABLE)
        component.set_editor_property("focus_settings", focus)

        self.queue = list(SAMPLE_TIMES)
        self.pending = None
        self.settling = None
        self.records = []
        self.warmup = 90
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def tick(self, _delta):
        if self.warmup:
            self.warmup -= 1
            return
        if self.pending is not None:
            sample_time, path, started = self.pending
            if path.is_file() and path.stat().st_size > 24:
                self.records.append({
                    "timeSeconds": sample_time,
                    "file": str(path),
                    "sha256": _sha256(path),
                    "sizeBytes": path.stat().st_size,
                })
                self.pending = None
                self.warmup = 20
            elif time.monotonic() - started > 120:
                raise RuntimeError(f"capture timeout: {path}")
            return
        if self.settling is not None:
            sample_time, ready_at = self.settling
            if time.monotonic() < ready_at:
                return
            self.face.set_play_rate(0.0)
            path = self.output / "frames" / f"face-{sample_time:04.1f}s.png"
            self.pending = (sample_time, path, time.monotonic())
            self.settling = None
            unreal.AutomationLibrary.take_high_res_screenshot(1600, 1600, str(path), self.camera)
            return
        if self.queue:
            sample_time = self.queue.pop(0)
            self.face.play(False)
            self.face.set_position(sample_time, False)
            self.face.set_play_rate(1.0)
            self.settling = (sample_time, time.monotonic() + 0.25)
            return
        report = {
            "schemaVersion": 1,
            "iteration": "v093",
            "state": "captured-draft-talking-playback",
            "map": MAP,
            "character": CHARACTER_LABEL,
            "animation": ANIMATION,
            "sampleTimesSeconds": list(SAMPLE_TIMES),
            "frames": self.records,
            "editorRuntimeVerified": True,
            "humanApproved": False,
            "productionReady": False,
            "automaticApproval": False,
        }
        (self.output / "capture-report.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        unreal.unregister_slate_post_tick_callback(self.handle)
        unreal.log(f"Gahyeon talking playback v093 completed: {self.output}")
        unreal.SystemLibrary.quit_editor()


def main():
    global _driver
    if _driver is not None:
        raise RuntimeError("v093 capture is already running")
    _driver = TalkingPlaybackCaptureV093()


main()
