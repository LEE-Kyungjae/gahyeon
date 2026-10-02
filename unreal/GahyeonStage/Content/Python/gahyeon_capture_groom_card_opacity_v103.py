"""Capture the v102b Groom card opacity probe with the fixed close-up camera."""

import hashlib
import json
import time
from pathlib import Path

import unreal


MAP = "/Game/Gahyeon/CharacterPipeline/v102b/Preview/L_Skotukeda_CardOpacityProbe_v102b"
LABEL = "Skotukeda_WardrobeGroomHigh_v095"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v103-groom-card-opacity-render/face-closeup.png"
)
REPORT = OUTPUT.with_suffix(".capture.json")
_driver = None


class Driver:
    def __init__(self):
        if OUTPUT.exists() or REPORT.exists():
            raise RuntimeError("refusing to overwrite immutable v103 capture")
        if unreal.EditorLoadingAndSavingUtils.load_map(MAP) is None:
            raise RuntimeError(f"failed to load v102b map: {MAP}")
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        character = next((actor for actor in actors.get_all_level_actors() if actor.get_actor_label() == LABEL), None)
        if character is None:
            raise RuntimeError(f"v095 High character unavailable: {LABEL}")
        origin, extent = character.get_actor_bounds(False, True)
        if not 130.0 <= extent.z * 2.0 <= 260.0:
            raise RuntimeError(f"unexpected character height: {extent.z * 2.0}")
        target = unreal.Vector(origin.x, origin.y, origin.z + extent.z * 0.82)
        location = target + unreal.Vector(0.0, 150.0, 0.0)
        self.camera = actors.spawn_actor_from_class(unreal.CineCameraActor, location)
        self.camera.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(location, target), False)
        component = self.camera.get_cine_camera_component()
        component.set_editor_property("current_focal_length", 55.0)
        component.set_editor_property("current_aperture", 8.0)
        focus = component.get_editor_property("focus_settings")
        focus.set_editor_property("focus_method", unreal.CameraFocusMethod.DISABLE)
        component.set_editor_property("focus_settings", focus)
        self.bounds = {"origin": [origin.x, origin.y, origin.z], "extent": [extent.x, extent.y, extent.z]}
        self.warmup = 240
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
                "iteration": "v103",
                "state": "captured-diagnostic-groom-card-opacity-probe",
                "hypothesis": "Reducing inherited Groom card opacity multipliers from 2.0 to 0.35 restores strand coverage instead of opaque card polygons.",
                "baseline": "v098",
                "map": MAP,
                "file": str(OUTPUT),
                "sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
                "characterBounds": self.bounds,
                "cameraTargetHeightFactor": 0.82,
                "cameraDistanceCm": 150.0,
                "manualGroomOffset": False,
                "automaticApproval": False,
                "productionReady": False,
            }, indent=2) + "\n")
            unreal.unregister_slate_post_tick_callback(self.handle)
            unreal.SystemLibrary.quit_editor()
        elif time.monotonic() - self.started > 180:
            unreal.unregister_slate_post_tick_callback(self.handle)
            raise RuntimeError("v103 capture timed out")


def capture_card_opacity_probe():
    global _driver
    _driver = Driver()


capture_card_opacity_probe()
