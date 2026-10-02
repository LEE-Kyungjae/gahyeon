"""Capture a brighter immutable diagnostic of the Stella v664 MetaHuman."""

import hashlib
import json
import time
from pathlib import Path

import unreal


MAP = "/Game/LivingCharacterPOC/v665/Preview/L_StellaMetaHumanQA_v665"
LABEL = "StellaLily_MetaHumanMedium_v664"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/"
    "living-character-poc-v667-stella-metahuman-lit-qa/renders"
)
VIEWS = (
    ("face-front", 0.0, 170.0, 0.82, 55.0),
    ("face-left45", -120.2, 120.2, 0.82, 55.0),
    ("full-body-front", 0.0, 480.0, 0.50, 55.0),
)
_driver_v667 = None


class StellaMetaHumanLitQAV667:
    def __init__(self):
        if OUTPUT.exists():
            raise RuntimeError(f"refusing to overwrite immutable v667 renders: {OUTPUT}")
        unreal.EditorPythonScripting.set_keep_python_script_alive(True)
        if unreal.EditorLoadingAndSavingUtils.load_map(MAP) is None:
            raise RuntimeError(f"failed to load v665 QA map: {MAP}")
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        level_actors = actors.get_all_level_actors()
        character = next(
            (actor for actor in level_actors if actor.get_actor_label() == LABEL), None
        )
        if character is None:
            raise RuntimeError(f"Stella v664 character unavailable: {LABEL}")
        rect_intensities = {
            "KEY_Stella_v665": 12000.0,
            "FILL_Stella_v665": 7000.0,
            "RIM_Stella_v665": 9000.0,
        }
        for actor in level_actors:
            label = actor.get_actor_label()
            if label in rect_intensities:
                actor.get_component_by_class(unreal.RectLightComponent).set_editor_property(
                    "intensity", rect_intensities[label]
                )
            if label == "SKY_Stella_v665":
                actor.get_component_by_class(unreal.SkyLightComponent).set_editor_property(
                    "intensity", 1.5
                )
            if label == "PPV_Stella_v665":
                settings = actor.get_editor_property("settings")
                settings.set_editor_property("auto_exposure_bias", 2.5)
                actor.set_editor_property("settings", settings)
        self.origin, self.extent = character.get_actor_bounds(False, True)
        height = self.extent.z * 2.0
        if not 130.0 <= height <= 260.0:
            raise RuntimeError(f"unexpected character height: {height}")
        self.camera = actors.spawn_actor_from_class(unreal.CineCameraActor, self.origin)
        component = self.camera.get_cine_camera_component()
        component.set_editor_property("current_aperture", 8.0)
        focus = component.get_editor_property("focus_settings")
        focus.set_editor_property("focus_method", unreal.CameraFocusMethod.DISABLE)
        component.set_editor_property("focus_settings", focus)
        OUTPUT.mkdir(parents=True, exist_ok=False)
        self.index = 0
        self.records = []
        self.handle = unreal.register_slate_post_tick_callback(self.tick)
        self.prepare_view()

    def prepare_view(self):
        name, x, y, height_factor, focal_length = VIEWS[self.index]
        target = unreal.Vector(
            self.origin.x,
            self.origin.y,
            self.origin.z + self.extent.z * height_factor,
        )
        location = target + unreal.Vector(x, y, 0.0)
        self.camera.set_actor_location(location, False, False)
        self.camera.set_actor_rotation(
            unreal.MathLibrary.find_look_at_rotation(location, target), False
        )
        self.camera.get_cine_camera_component().set_editor_property(
            "current_focal_length", focal_length
        )
        self.current = {
            "view": name,
            "file": str(OUTPUT / f"{name}.png"),
            "location": [location.x, location.y, location.z],
            "target": [target.x, target.y, target.z],
        }
        self.warmup = 300 if self.index == 0 else 90
        self.started = None

    def tick(self, _delta):
        if self.warmup:
            self.warmup -= 1
            return
        image = Path(self.current["file"])
        if self.started is None:
            self.started = time.monotonic()
            unreal.AutomationLibrary.take_high_res_screenshot(
                1200, 1200, str(image), self.camera
            )
            return
        if image.is_file() and image.stat().st_size > 24:
            self.current["width"] = 1200
            self.current["height"] = 675
            self.current["sha256"] = hashlib.sha256(image.read_bytes()).hexdigest()
            self.current["sizeBytes"] = image.stat().st_size
            self.records.append(self.current)
            self.index += 1
            if self.index < len(VIEWS):
                self.prepare_view()
                return
            self.finish()
        elif time.monotonic() - self.started > 180:
            raise RuntimeError(f"v667 capture timed out: {image}")

    def finish(self):
        (OUTPUT.parent / "capture-report.json").write_text(json.dumps({
            "schemaVersion": 1,
            "iteration": "v667",
            "state": "captured-brightness-corrected-draft-metahuman",
            "sourceAssembly": "v664",
            "sourceMap": MAP,
            "runtimeOnlyLightingOverride": {
                "rectLightIntensities": [12000.0, 7000.0, 9000.0],
                "skyIntensity": 1.5,
                "exposureBias": 2.5,
            },
            "views": self.records,
            "automaticApproval": False,
            "productionReady": False,
        }, indent=2) + "\n", encoding="utf-8")
        unreal.unregister_slate_post_tick_callback(self.handle)
        unreal.EditorPythonScripting.set_keep_python_script_alive(False)
        unreal.SystemLibrary.quit_editor()


def capture_stella_metahuman_lit_qa_v667():
    global _driver_v667
    _driver_v667 = StellaMetaHumanLitQAV667()


capture_stella_metahuman_lit_qa_v667()
