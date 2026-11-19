"""Capture an immutable five-view sane MetaHuman recovery baseline in UE 5.8."""

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import unreal


MAP = "/Game/Gahyeon/CharacterPipeline/v027/Preview/L_Skotukeda_Medium_v027"
ACTOR_LABEL = "Skotukeda_Medium_v027"
BLUEPRINT = (
    "/Game/Gahyeon/CharacterPipeline/v027/AssembledMedium/Skotukeda_Medium_v027/"
    "BP_Skotukeda_Medium_v027"
)
VIEWS = (
    ("face-front", (0.0, 180.0, 165.0)),
    ("face-left-45", (-127.279, 127.279, 165.0)),
    ("face-right-45", (127.279, 127.279, 165.0)),
    ("face-left-profile", (-180.0, 0.0, 165.0)),
    ("face-right-profile", (180.0, 0.0, 165.0)),
)
TARGET = unreal.Vector(0.0, 0.0, 165.0)
_driver = None


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class RecoveryBaselineCapture:
    def __init__(self):
        workspace = Path(os.environ.get("GAHYEON_WORKSPACE", "/Users/ze/work/gahyeonbot")).resolve()
        self.iteration = os.environ.get("GAHYEON_RECOVERY_BASELINE_ITERATION", "v074")
        if self.iteration != "v074":
            raise RuntimeError(f"only the immutable v074 recovery baseline is supported: {self.iteration}")
        self.output = workspace / f"artifacts/gahyeon-ch/iterations/{self.iteration}-template-baseline/ue-five-view"
        if self.output.exists():
            raise RuntimeError(f"refusing to overwrite immutable v073 baseline: {self.output}")
        world = unreal.EditorLoadingAndSavingUtils.load_map(MAP)
        if world is None:
            raise RuntimeError(f"recovery baseline map is unavailable: {MAP}")
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        characters = [a for a in actors.get_all_level_actors() if a.get_actor_label() == ACTOR_LABEL]
        if len(characters) != 1:
            raise RuntimeError(f"expected one sane baseline actor, got {len(characters)}")
        self.character = characters[0]
        self.camera = actors.spawn_actor_from_class(unreal.CineCameraActor, unreal.Vector())
        if self.camera is None:
            raise RuntimeError("failed to create sealed v073 QA camera")
        self.camera.set_actor_label("CAM_Gahyeon_Recovery_v073")
        component = self.camera.get_cine_camera_component()
        component.set_editor_property("current_focal_length", 85.0)
        component.set_editor_property("current_aperture", 8.0)
        component.set_editor_property("constrain_aspect_ratio", False)
        focus = component.get_editor_property("focus_settings")
        focus.set_editor_property("focus_method", unreal.CameraFocusMethod.DISABLE)
        component.set_editor_property("focus_settings", focus)
        self.output.mkdir(parents=True)
        self.queue = list(VIEWS)
        self.pending = None
        self.renders = []
        self.handle = None
        self.warmup = 45

    def start(self):
        self.handle = unreal.register_slate_post_tick_callback(self.tick)
        unreal.log("Gahyeon v073 sane MetaHuman recovery baseline capture started")

    def fail(self, error):
        if self.handle is not None:
            unreal.unregister_slate_post_tick_callback(self.handle)
            self.handle = None
        (self.output / "failure.json").write_text(
            json.dumps({"state": "failed", "error": str(error)}, indent=2) + "\n",
            encoding="utf-8",
        )
        unreal.log_error(str(error))

    def begin_capture(self, view, coordinates):
        location = unreal.Vector(*coordinates)
        rotation = unreal.MathLibrary.find_look_at_rotation(location, TARGET)
        self.camera.set_actor_location_and_rotation(location, rotation, False, False)
        target = self.output / f"{view}.png"
        self.pending = (view, target, location, rotation, time.monotonic())
        unreal.AutomationLibrary.take_high_res_screenshot(1440, 2560, str(target), self.camera)

    def finish(self):
        manifest = {
            "schemaVersion": 1,
            "jobId": f"gahyeon-metahuman-template-baseline-{self.iteration}",
            "state": "captured-sane-template-baseline",
            "observedAt": datetime.now(timezone.utc).isoformat(),
            "iteration": self.iteration,
            "engineVersion": unreal.SystemLibrary.get_engine_version(),
            "sourceMap": MAP,
            "sourceBlueprint": BLUEPRINT,
            "heroActorPath": self.character.get_path_name(),
            "editorRuntimeVerified": True,
            "headOnlyCheckpoint": True,
            "profile": "desktop-first-looking-glass-go-framing",
            "resolution": [1440, 2560],
            "background": "fixed-v027-neutral-qa",
            "cameraContract": {"focalLengthMm": 85.0, "aperture": 8.0, "targetCm": [0.0, 0.0, 165.0]},
            "renders": self.renders,
            "identityAuthority": "sane-metahuman-template-baseline-not-gahyeon-canon",
            "automaticApproval": False,
            "productionReady": False,
            "qualityClaim": None,
        }
        (self.output / "render-manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        unreal.unregister_slate_post_tick_callback(self.handle)
        self.handle = None
        unreal.log(f"Gahyeon v073 recovery baseline captured: {self.output}")

    def tick(self, _delta_seconds):
        try:
            if self.warmup:
                self.warmup -= 1
                return
            if self.pending:
                view, target, location, rotation, started = self.pending
                if target.is_file() and target.stat().st_size > 24:
                    self.renders.append({
                        "view": view,
                        "uri": target.name,
                        "sha256": sha256(target),
                        "camera": {
                            "actorPath": self.camera.get_path_name(),
                            "location": [location.x, location.y, location.z],
                            "rotation": [rotation.roll, rotation.pitch, rotation.yaw],
                            "focalLengthMm": 85.0,
                        },
                    })
                    self.pending = None
                    self.warmup = 12
                elif time.monotonic() - started > 180:
                    raise RuntimeError(f"v073 baseline capture timed out: {view}")
                return
            if self.queue:
                self.begin_capture(*self.queue.pop(0))
                return
            self.finish()
        except Exception as exc:
            self.fail(exc)


def main():
    global _driver
    if _driver is not None:
        raise RuntimeError("v073 recovery baseline capture already running")
    _driver = RecoveryBaselineCapture()
    _driver.start()


main()
