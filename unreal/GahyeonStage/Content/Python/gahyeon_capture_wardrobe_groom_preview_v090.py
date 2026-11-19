"""Capture a wider, uncropped QA image from the official Wardrobe assembly."""

import hashlib
import json
import time
from pathlib import Path

import unreal


MAP = "/Game/Gahyeon/CharacterPipeline/v089/Preview/L_Skotukeda_WardrobeGroom_v089"
LABEL = "Skotukeda_WardrobeGroomQA_v088"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v090-official-wardrobe-groom-wide/head-and-shoulders.png"
)
REPORT = OUTPUT.with_suffix(".capture.json")
_driver = None


class Driver:
    def __init__(self):
        if OUTPUT.exists() or REPORT.exists():
            raise RuntimeError("refusing to overwrite immutable v090 capture")
        if unreal.EditorLoadingAndSavingUtils.load_map(MAP) is None:
            raise RuntimeError(f"failed to load v089 map: {MAP}")
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        character = next((a for a in actors.get_all_level_actors() if a.get_actor_label() == LABEL), None)
        if character is None:
            raise RuntimeError(f"v089 character unavailable: {LABEL}")
        bounds_origin, bounds_extent = character.get_actor_bounds(False, True)
        height = bounds_extent.z * 2.0
        if not 130.0 <= height <= 260.0:
            raise RuntimeError(f"unexpected character height: {height}")

        # The high-resolution screenshot inherits the live 16:9 viewport aspect.
        # Aim above the bust center and leave generous headroom instead of assuming
        # the requested pixel dimensions establish a square camera gate.
        target = unreal.Vector(bounds_origin.x, bounds_origin.y, bounds_origin.z + bounds_extent.z * 0.68)
        location = target + unreal.Vector(0.0, 265.0, 0.0)
        self.camera = actors.spawn_actor_from_class(unreal.CineCameraActor, location)
        self.camera.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(location, target), False)
        component = self.camera.get_cine_camera_component()
        component.set_editor_property("current_focal_length", 55.0)
        component.set_editor_property("current_aperture", 8.0)
        focus = component.get_editor_property("focus_settings")
        focus.set_editor_property("focus_method", unreal.CameraFocusMethod.DISABLE)
        component.set_editor_property("focus_settings", focus)
        self.bounds = {
            "origin": [bounds_origin.x, bounds_origin.y, bounds_origin.z],
            "extent": [bounds_extent.x, bounds_extent.y, bounds_extent.z],
        }
        self.warmup = 180
        self.started = None
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def tick(self, _delta):
        if self.warmup:
            self.warmup -= 1
            return
        if self.started is None:
            OUTPUT.parent.mkdir(parents=True, exist_ok=False)
            self.started = time.monotonic()
            unreal.AutomationLibrary.take_high_res_screenshot(1600, 900, str(OUTPUT), self.camera)
            return
        if OUTPUT.is_file() and OUTPUT.stat().st_size > 24:
            REPORT.write_text(json.dumps({
                "schemaVersion": 1,
                "iteration": "v090",
                "state": "captured-draft-official-wardrobe-groom-wide",
                "map": MAP,
                "file": str(OUTPUT),
                "sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
                "characterBounds": self.bounds,
                "cameraTargetHeightFactor": 0.68,
                "cameraDistanceCm": 265.0,
                "manualGroomOffset": False,
                "automaticApproval": False,
                "productionReady": False,
            }, indent=2) + "\n")
            unreal.unregister_slate_post_tick_callback(self.handle)
            unreal.SystemLibrary.quit_editor()
        elif time.monotonic() - self.started > 180:
            unreal.unregister_slate_post_tick_callback(self.handle)
            raise RuntimeError("v090 capture timed out")


def main():
    global _driver
    _driver = Driver()


main()
