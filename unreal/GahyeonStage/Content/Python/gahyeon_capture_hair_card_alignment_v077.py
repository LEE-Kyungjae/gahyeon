"""Capture the immutable v077 aligned-hair close-up."""

import hashlib
import json
import time
from pathlib import Path

import unreal


MAP = "/Game/Gahyeon/CharacterPipeline/v077/Preview/L_Skotukeda_HairCardAligned_v077"
CAMERA_LABEL = "CAM_Gahyeon_HeadQA_v077"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v077-hair-card-alignment/head-front.png"
)
REPORT = OUTPUT.with_suffix(".capture.json")
_driver = None


class CaptureDriver:
    def __init__(self):
        if OUTPUT.exists() or REPORT.exists():
            raise RuntimeError(f"refusing to overwrite immutable v077 capture: {OUTPUT}")
        world = unreal.EditorLoadingAndSavingUtils.load_map(MAP)
        if world is None:
            raise RuntimeError(f"failed to load v077 map: {MAP}")
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
        self.camera = next((actor for actor in actors if actor.get_actor_label() == CAMERA_LABEL), None)
        if self.camera is None or not isinstance(self.camera, unreal.CineCameraActor):
            raise RuntimeError(f"sealed v077 camera is unavailable: {CAMERA_LABEL}")
        self.warmup = 45
        self.started = None
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def tick(self, _delta):
        if self.warmup:
            self.warmup -= 1
            return
        if self.started is None:
            self.started = time.monotonic()
            unreal.AutomationLibrary.take_high_res_screenshot(900, 1200, str(OUTPUT), self.camera)
            return
        if OUTPUT.is_file() and OUTPUT.stat().st_size > 24:
            REPORT.write_text(
                json.dumps(
                    {
                        "schemaVersion": 1,
                        "iteration": "v077",
                        "state": "captured-draft-hair-card-alignment",
                        "map": MAP,
                        "camera": CAMERA_LABEL,
                        "resolution": [900, 1200],
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
            unreal.log(f"Gahyeon v077 head capture complete: {OUTPUT}")
            unreal.SystemLibrary.quit_editor()
        elif time.monotonic() - self.started > 120:
            unreal.unregister_slate_post_tick_callback(self.handle)
            self.handle = None
            raise RuntimeError("v077 head capture timed out")


def main():
    global _driver
    _driver = CaptureDriver()


main()
