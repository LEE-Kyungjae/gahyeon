"""Build and capture v186 with a fixed 180 cm MetaHuman QA frame."""

import hashlib
import json
import time
from pathlib import Path

import unreal


BLUEPRINT_PATH = (
    "/Game/Gahyeon/CharacterPipeline/v186/AssembledMedium/"
    "Gahyeon_KeenToolsMedium_v186/BP_Gahyeon_KeenToolsMedium_v186"
)
MAP_PATH = "/Game/Gahyeon/CharacterPipeline/v189/Preview/L_KeenToolsStandardBoundsQA_v189"
ROOT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v189-metahuman-keentools-standard-bounds-qa"
)
OUTPUT = ROOT / "renders"
VIEWS = (
    ("face-front", 0.0, 170.0, 147.6, 55.0),
    ("face-left45", -120.2, 120.2, 147.6, 55.0),
    ("face-right45", 120.2, 120.2, 147.6, 55.0),
    ("face-left90", -170.0, 0.0, 147.6, 55.0),
    ("face-right90", 170.0, 0.0, 147.6, 55.0),
    ("bust-front", 0.0, 280.0, 120.6, 55.0),
    ("full-body-front", 0.0, 480.0, 90.0, 55.0),
)
_driver_v189 = None


def _rect_light_v189(actors, label, location, target, intensity, width, height):
    light = actors.spawn_actor_from_class(
        unreal.RectLight,
        location,
        unreal.MathLibrary.find_look_at_rotation(location, target),
    )
    if light is None:
        raise RuntimeError(f"failed to spawn {label}")
    light.set_actor_label(label)
    component = light.get_component_by_class(unreal.RectLightComponent)
    component.set_editor_property("intensity", intensity)
    component.set_editor_property("source_width", width)
    component.set_editor_property("source_height", height)
    return light


class GahyeonKeenToolsStandardBoundsQaV189:
    def __init__(self):
        if ROOT.exists() or unreal.EditorAssetLibrary.does_asset_exist(MAP_PATH):
            raise RuntimeError("refusing to overwrite immutable v189 QA outputs")
        unreal.EditorPythonScripting.set_keep_python_script_alive(True)
        character_class = unreal.EditorAssetLibrary.load_blueprint_class(BLUEPRINT_PATH)
        if character_class is None:
            raise RuntimeError(f"v186 Blueprint unavailable: {BLUEPRINT_PATH}")
        if not unreal.EditorLevelLibrary.new_level(MAP_PATH):
            raise RuntimeError(f"failed to create QA level: {MAP_PATH}")
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        self.character = actors.spawn_actor_from_class(character_class, unreal.Vector())
        if self.character is None:
            raise RuntimeError("failed to spawn v186 assembled MetaHuman")
        self.character.set_actor_label("Gahyeon_KeenToolsMedium_v186")

        face_target = unreal.Vector(0.0, 0.0, 147.6)
        _rect_light_v189(
            actors, "KEY_KeenTools_v189",
            face_target + unreal.Vector(-120.0, 180.0, 70.0), face_target,
            18000.0, 110.0, 110.0,
        )
        _rect_light_v189(
            actors, "FILL_KeenTools_v189",
            face_target + unreal.Vector(130.0, 150.0, 25.0), face_target,
            9000.0, 100.0, 100.0,
        )
        _rect_light_v189(
            actors, "RIM_KeenTools_v189",
            face_target + unreal.Vector(0.0, -130.0, 55.0), face_target,
            12000.0, 85.0, 100.0,
        )
        sky = actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector())
        sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("intensity", 0.65)
        post = actors.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector())
        post.set_editor_property("unbound", True)
        settings = post.get_editor_property("settings")
        settings.set_editor_property("override_auto_exposure_method", True)
        settings.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)
        settings.set_editor_property("override_auto_exposure_bias", True)
        settings.set_editor_property("auto_exposure_bias", 3.0)
        post.set_editor_property("settings", settings)
        if not unreal.EditorLevelLibrary.save_current_level():
            raise RuntimeError(f"failed to save QA level: {MAP_PATH}")

        ROOT.mkdir(parents=True, exist_ok=False)
        OUTPUT.mkdir()
        raw_origin, raw_extent = self.character.get_actor_bounds(False, True)
        (ROOT / "build-report.json").write_text(json.dumps({
            "schemaVersion": 1,
            "iteration": "v189",
            "state": "built-standard-180cm-fixed-camera-qa-map",
            "sourceAssembly": "v186",
            "blueprint": BLUEPRINT_PATH,
            "map": MAP_PATH,
            "cameraFrame": {"heightCm": 180.0, "origin": [0.0, 0.0, 90.0]},
            "rawActorBounds": {
                "origin": list(raw_origin.to_tuple()),
                "extent": list(raw_extent.to_tuple()),
                "heightCm": raw_extent.z * 2.0,
                "excludedFromCameraFit": True,
            },
            "automaticApproval": False,
            "productionReady": False,
        }, indent=2) + "\n", encoding="utf-8")
        self.camera = actors.spawn_actor_from_class(unreal.CineCameraActor, unreal.Vector())
        component = self.camera.get_cine_camera_component()
        component.set_editor_property("current_aperture", 8.0)
        focus = component.get_editor_property("focus_settings")
        focus.set_editor_property("focus_method", unreal.CameraFocusMethod.DISABLE)
        component.set_editor_property("focus_settings", focus)
        self.index = 0
        self.records = []
        self.handle = unreal.register_slate_post_tick_callback(self.tick)
        self.prepare_view()

    def prepare_view(self):
        name, x, y, target_z, focal_length = VIEWS[self.index]
        target = unreal.Vector(0.0, 0.0, target_z)
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
            "target": list(target.to_tuple()),
            "location": list(location.to_tuple()),
            "focalLengthMm": focal_length,
            "file": str(OUTPUT / f"{name}.png"),
        }
        self.warmup = 300 if self.index == 0 else 75
        self.started = None

    def tick(self, _delta):
        if self.warmup:
            self.warmup -= 1
            return
        image = Path(self.current["file"])
        if self.started is None:
            self.started = time.monotonic()
            unreal.AutomationLibrary.take_high_res_screenshot(1200, 1200, str(image), self.camera)
            return
        if image.is_file() and image.stat().st_size > 24:
            self.current["sha256"] = hashlib.sha256(image.read_bytes()).hexdigest()
            self.current["sizeBytes"] = image.stat().st_size
            self.records.append(self.current)
            self.index += 1
            if self.index < len(VIEWS):
                self.prepare_view()
                return
            self.finish()
        elif time.monotonic() - self.started > 180:
            raise RuntimeError(f"v189 capture timed out: {image}")

    def finish(self):
        (ROOT / "capture-report.json").write_text(json.dumps({
            "schemaVersion": 1,
            "iteration": "v189",
            "state": "captured-draft-keentools-metahuman-seven-view",
            "sourceAssembly": "v186",
            "views": self.records,
            "automaticApproval": False,
            "productionReady": False,
        }, indent=2) + "\n", encoding="utf-8")
        unreal.unregister_slate_post_tick_callback(self.handle)
        unreal.EditorPythonScripting.set_keep_python_script_alive(False)
        unreal.SystemLibrary.quit_editor()


def build_and_capture_keentools_qa_v189():
    global _driver_v189
    _driver_v189 = GahyeonKeenToolsStandardBoundsQaV189()


build_and_capture_keentools_qa_v189()
