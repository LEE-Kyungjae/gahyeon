"""Capture the anomalous v186 raw bounds to identify the assembly scale defect."""

import hashlib
import json
import time
from pathlib import Path

import unreal


BLUEPRINT_PATH = (
    "/Game/Gahyeon/CharacterPipeline/v186/AssembledMedium/"
    "Gahyeon_KeenToolsMedium_v186/BP_Gahyeon_KeenToolsMedium_v186"
)
ROOT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v190-metahuman-keentools-raw-bounds-diagnostic"
)
_driver_v190 = None


class GahyeonKeenToolsRawBoundsQaV190:
    def __init__(self):
        if ROOT.exists():
            raise RuntimeError("refusing to overwrite immutable v190 diagnostic")
        unreal.EditorPythonScripting.set_keep_python_script_alive(True)
        character_class = unreal.EditorAssetLibrary.load_blueprint_class(BLUEPRINT_PATH)
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        self.character = actors.spawn_actor_from_class(character_class, unreal.Vector())
        if self.character is None:
            raise RuntimeError("failed to spawn v186 assembled MetaHuman")
        self.origin, self.extent = self.character.get_actor_bounds(False, True)
        if self.extent.z * 2.0 < 1000.0:
            raise RuntimeError("v186 raw-bounds anomaly no longer reproduces")
        for yaw, pitch, intensity in ((-35.0, -25.0, 5.0), (35.0, -15.0, 3.0), (180.0, -10.0, 4.0)):
            light = actors.spawn_actor_from_class(
                unreal.DirectionalLight, unreal.Vector(), unreal.Rotator(pitch, yaw, 0.0)
            )
            light.get_component_by_class(unreal.DirectionalLightComponent).set_editor_property(
                "intensity", intensity
            )
        sky = actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector())
        sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("intensity", 1.0)
        post = actors.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector())
        post.set_editor_property("unbound", True)
        settings = post.get_editor_property("settings")
        settings.set_editor_property("override_auto_exposure_method", True)
        settings.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)
        settings.set_editor_property("override_auto_exposure_bias", True)
        settings.set_editor_property("auto_exposure_bias", 1.5)
        post.set_editor_property("settings", settings)
        self.camera = actors.spawn_actor_from_class(unreal.CineCameraActor, self.origin)
        camera = self.camera.get_cine_camera_component()
        camera.set_editor_property("current_aperture", 8.0)
        camera.set_editor_property("current_focal_length", 55.0)
        focus = camera.get_editor_property("focus_settings")
        focus.set_editor_property("focus_method", unreal.CameraFocusMethod.DISABLE)
        camera.set_editor_property("focus_settings", focus)
        ROOT.mkdir(parents=True, exist_ok=False)
        self.views = (
            ("raw-full-front", self.origin, self.extent.z * 3.0),
            (
                "raw-upper-front",
                unreal.Vector(self.origin.x, self.origin.y, self.origin.z + self.extent.z * 0.55),
                self.extent.z * 1.35,
            ),
        )
        self.index = 0
        self.records = []
        self.handle = unreal.register_slate_post_tick_callback(self.tick)
        self.prepare()

    def prepare(self):
        name, target, distance = self.views[self.index]
        location = target + unreal.Vector(0.0, distance, 0.0)
        self.camera.set_actor_location(location, False, False)
        self.camera.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(location, target), False)
        self.current = {"view": name, "target": list(target.to_tuple()), "distance": distance}
        self.image = ROOT / f"{name}.png"
        self.warmup = 300 if self.index == 0 else 75
        self.started = None

    def tick(self, _delta):
        if self.warmup:
            self.warmup -= 1
            return
        if self.started is None:
            self.started = time.monotonic()
            unreal.AutomationLibrary.take_high_res_screenshot(1200, 1200, str(self.image), self.camera)
            return
        if self.image.is_file() and self.image.stat().st_size > 24:
            self.current["file"] = str(self.image)
            self.current["sha256"] = hashlib.sha256(self.image.read_bytes()).hexdigest()
            self.records.append(self.current)
            self.index += 1
            if self.index < len(self.views):
                self.prepare()
                return
            self.finish()
        elif time.monotonic() - self.started > 180:
            raise RuntimeError(f"v190 capture timed out: {self.image}")

    def finish(self):
        (ROOT / "report.json").write_text(json.dumps({
            "schemaVersion": 1,
            "iteration": "v190",
            "state": "captured-raw-bounds-scale-diagnostic",
            "sourceAssembly": "v186",
            "rawBounds": {
                "origin": list(self.origin.to_tuple()),
                "extent": list(self.extent.to_tuple()),
                "heightCm": self.extent.z * 2.0,
            },
            "views": self.records,
            "automaticApproval": False,
            "productionReady": False,
        }, indent=2) + "\n", encoding="utf-8")
        unreal.unregister_slate_post_tick_callback(self.handle)
        unreal.EditorPythonScripting.set_keep_python_script_alive(False)
        unreal.SystemLibrary.quit_editor()


def capture_keentools_raw_bounds_v190():
    global _driver_v190
    _driver_v190 = GahyeonKeenToolsRawBoundsQaV190()


capture_keentools_raw_bounds_v190()
