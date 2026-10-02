"""Capture v077 from a wider temporary bust camera without modifying the sealed map."""

import hashlib
import json
import time
from pathlib import Path

import unreal


MAP = "/Game/Gahyeon/CharacterPipeline/v077/Preview/L_Skotukeda_HairCardAligned_v077"
CHARACTER_LABEL = "Skotukeda_Medium_v027"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v077-hair-card-alignment/head-bust-wide.png"
)
REPORT = OUTPUT.with_suffix(".capture.json")
_driver = None


class WideCaptureDriver:
    def __init__(self):
        if OUTPUT.exists() or REPORT.exists():
            raise RuntimeError(f"refusing to overwrite immutable v077 wide capture: {OUTPUT}")
        world = unreal.EditorLoadingAndSavingUtils.load_map(MAP)
        if world is None:
            raise RuntimeError(f"failed to load v077 map: {MAP}")
        actor_system = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        actors = actor_system.get_all_level_actors()
        character = next((actor for actor in actors if actor.get_actor_label() == CHARACTER_LABEL), None)
        if character is None:
            raise RuntimeError(f"character actor is unavailable: {CHARACTER_LABEL}")

        target = character.get_actor_location() + unreal.Vector(0.0, 0.0, 150.0)
        location = target + unreal.Vector(0.0, 170.0, 2.0)
        self.camera = actor_system.spawn_actor_from_class(unreal.CineCameraActor, location)
        if self.camera is None:
            raise RuntimeError("failed to spawn temporary v077 wide camera")
        self.camera.set_actor_label("CAM_Gahyeon_HeadBustWide_v077")
        self.camera.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(location, target), False)
        component = self.camera.get_cine_camera_component()
        component.set_editor_property("current_focal_length", 85.0)
        component.set_editor_property("current_aperture", 8.0)
        focus = component.get_editor_property("focus_settings")
        focus.set_editor_property("focus_method", unreal.CameraFocusMethod.DISABLE)
        component.set_editor_property("focus_settings", focus)

        self.warmup = 45
        self.started = None
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def tick(self, _delta):
        if self.warmup:
            self.warmup -= 1
            return
        if self.started is None:
            self.started = time.monotonic()
            unreal.AutomationLibrary.take_high_res_screenshot(1200, 1200, str(OUTPUT), self.camera)
            return
        if OUTPUT.is_file() and OUTPUT.stat().st_size > 24:
            REPORT.write_text(
                json.dumps(
                    {
                        "schemaVersion": 1,
                        "iteration": "v077",
                        "state": "captured-draft-wide-inspection",
                        "map": MAP,
                        "camera": self.camera.get_actor_label(),
                        "cameraDistanceCm": 170.0,
                        "resolution": [1200, 1200],
                        "file": str(OUTPUT),
                        "sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
                        "automaticApproval": False,
                        "productionReady": False,
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            unreal.unregister_slate_post_tick_callback(self.handle)
            self.handle = None
            unreal.SystemLibrary.quit_editor()
        elif time.monotonic() - self.started > 120:
            unreal.unregister_slate_post_tick_callback(self.handle)
            self.handle = None
            raise RuntimeError("v077 wide capture timed out")


def main():
    global _driver
    _driver = WideCaptureDriver()


main()
