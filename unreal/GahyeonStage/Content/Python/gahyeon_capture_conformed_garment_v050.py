"""Capture the populated v050 preview from its fixed desktop QA camera."""

import hashlib
import json
import time
from pathlib import Path

import unreal


OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/garment-conform/v048/"
    "v050-render.png"
)
REPORT = OUTPUT.with_suffix(".json")
CAMERA_LABEL = "CAM_Gahyeon_Desktop_v025b"
_driver = None


class CaptureDriver:
    def __init__(self):
        if OUTPUT.exists() or REPORT.exists():
            raise RuntimeError(f"refusing to overwrite v050 capture: {OUTPUT}")
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
        self.camera = next(
            (actor for actor in actors if actor.get_actor_label() == CAMERA_LABEL), None
        )
        if self.camera is None or not isinstance(self.camera, unreal.CameraActor):
            raise RuntimeError(f"v050 fixed camera is unavailable: {CAMERA_LABEL}")
        self.started = None
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def tick(self, _delta):
        if self.started is None:
            unreal.AutomationLibrary.take_high_res_screenshot(
                1440, 1920, str(OUTPUT), self.camera
            )
            self.started = time.monotonic()
            return
        if OUTPUT.is_file() and OUTPUT.stat().st_size > 24:
            digest = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
            REPORT.write_text(
                json.dumps(
                    {
                        "schemaVersion": 1,
                        "iteration": "v050",
                        "camera": CAMERA_LABEL,
                        "resolution": [1440, 1920],
                        "file": str(OUTPUT),
                        "sha256": digest,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            unreal.unregister_slate_post_tick_callback(self.handle)
            unreal.log(f"Gahyeon v050 garment capture complete: {OUTPUT}")
        elif time.monotonic() - self.started > 120:
            unreal.unregister_slate_post_tick_callback(self.handle)
            raise RuntimeError("v050 garment capture timed out")


def main():
    global _driver
    _driver = CaptureDriver()


main()
