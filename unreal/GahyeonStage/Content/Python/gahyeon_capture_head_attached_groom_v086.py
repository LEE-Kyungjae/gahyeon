"""Capture v086 head-attached Groom."""

import hashlib
import json
import time
from pathlib import Path

import unreal


MAP = "/Game/Gahyeon/CharacterPipeline/v086/Preview/L_Skotukeda_HeadAttachedGroom_v086"
OUTPUT = Path("/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/v086-head-attached-groom/head-and-shoulders.png")
REPORT = OUTPUT.with_suffix(".capture.json")
_driver = None


class CaptureDriver:
    def __init__(self):
        if OUTPUT.exists() or REPORT.exists():
            raise RuntimeError(f"refusing to overwrite immutable v086 capture: {OUTPUT}")
        if unreal.EditorLoadingAndSavingUtils.load_map(MAP) is None:
            raise RuntimeError(f"failed to load v086 map: {MAP}")
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        character = next((a for a in actors.get_all_level_actors() if a.get_actor_label() == "Skotukeda_Medium_v027"), None)
        target = character.get_actor_location() + unreal.Vector(0.0, 0.0, 165.0)
        location = target + unreal.Vector(0.0, 180.0, 0.0)
        self.camera = actors.spawn_actor_from_class(unreal.CineCameraActor, location)
        self.camera.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(location, target), False)
        camera = self.camera.get_cine_camera_component()
        camera.set_editor_property("current_focal_length", 50.0)
        camera.set_editor_property("current_aperture", 8.0)
        focus = camera.get_editor_property("focus_settings")
        focus.set_editor_property("focus_method", unreal.CameraFocusMethod.DISABLE)
        camera.set_editor_property("focus_settings", focus)
        self.warmup = 120
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
            REPORT.write_text(json.dumps({
                "schemaVersion": 1, "iteration": "v086", "state": "captured-draft-head-attached-groom",
                "map": MAP, "file": str(OUTPUT), "sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
                "automaticApproval": False, "productionReady": False,
            }, indent=2) + "\n", encoding="utf-8")
            unreal.unregister_slate_post_tick_callback(self.handle)
            unreal.SystemLibrary.quit_editor()
        elif time.monotonic() - self.started > 180:
            unreal.unregister_slate_post_tick_callback(self.handle)
            raise RuntimeError("v086 capture timed out")


def main():
    global _driver
    _driver = CaptureDriver()


main()
