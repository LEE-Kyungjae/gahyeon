"""Render neutral v525 Ururu with v585 materials for conform preflight."""

import hashlib
import json
from pathlib import Path
import time

import unreal


NEUTRAL = "/Game/LivingCharacterPOC/v525/Characters/UruruPreview/Ururu_Normalized_v523"
TEXTURED = (
    "/Game/LivingCharacterPOC/v585/Characters/UruruCentimeterNormalized/"
    "Ururu_CentimeterNormalized_v584"
)
MAP = "/Game/LivingCharacterPOC/v673/Preview/L_UruruNeutralTexturedPortrait_v673"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/"
    "living-character-poc-v673-ururu-neutral-textured-portrait"
)
_driver_v673 = None


class UruruNeutralTexturedPortraitV673:
    def __init__(self):
        if OUTPUT.exists() or unreal.EditorAssetLibrary.does_asset_exist(MAP):
            raise RuntimeError("refusing to overwrite immutable v673 evidence")
        neutral = unreal.load_asset(NEUTRAL)
        textured = unreal.load_asset(TEXTURED)
        if neutral is None or textured is None:
            raise RuntimeError("required Ururu meshes are unavailable")
        neutral_slots = neutral.get_editor_property("materials")
        textured_slots = textured.get_editor_property("materials")
        neutral_names = [str(slot.material_slot_name) for slot in neutral_slots]
        textured_names = [str(slot.material_slot_name) for slot in textured_slots]
        if neutral_names != textured_names:
            raise RuntimeError("Ururu material slot order changed after v672 audit")
        OUTPUT.mkdir(parents=True, exist_ok=False)
        if not unreal.EditorLevelLibrary.new_level(MAP):
            raise RuntimeError("failed to create v673 portrait map")
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        character = actors.spawn_actor_from_class(
            unreal.SkeletalMeshActor, unreal.Vector(), unreal.Rotator()
        )
        character.set_actor_label("UruruNeutralTexturedPreview_v673")
        component = character.get_component_by_class(unreal.SkeletalMeshComponent)
        component.set_editor_property("skeletal_mesh_asset", neutral)
        borrowed = []
        for index, slot in enumerate(textured_slots):
            material = slot.material_interface
            if material is None:
                raise RuntimeError(f"missing v585 material at slot {index}")
            component.set_material(index, material)
            borrowed.append(material.get_path_name())
        self.origin, self.extent = character.get_actor_bounds(False, True)
        height = self.extent.z * 2.0
        if not 130.0 <= height <= 190.0:
            raise RuntimeError(f"implausible neutral Ururu height: {height}")
        self.target = unreal.Vector(
            self.origin.x, self.origin.y, self.origin.z + self.extent.z * 0.72
        )
        self.camera_location = self.target + unreal.Vector(0.0, 155.0, 0.0)
        self.camera = actors.spawn_actor_from_class(
            unreal.CineCameraActor,
            self.camera_location,
            unreal.MathLibrary.find_look_at_rotation(self.camera_location, self.target),
        )
        camera_component = self.camera.get_cine_camera_component()
        camera_component.set_editor_property("current_focal_length", 55.0)
        camera_component.set_editor_property("current_aperture", 8.0)
        focus = camera_component.get_editor_property("focus_settings")
        focus.set_editor_property("focus_method", unreal.CameraFocusMethod.DISABLE)
        camera_component.set_editor_property("focus_settings", focus)
        for offset, intensity in (
            (unreal.Vector(-85.0, 110.0, 45.0), 2600.0),
            (unreal.Vector(85.0, 100.0, 20.0), 1500.0),
            (unreal.Vector(0.0, -90.0, 55.0), 2000.0),
        ):
            location = self.target + offset
            light = actors.spawn_actor_from_class(
                unreal.RectLight,
                location,
                unreal.MathLibrary.find_look_at_rotation(location, self.target),
            )
            light_component = light.get_component_by_class(unreal.RectLightComponent)
            light_component.set_editor_property("intensity", intensity)
            light_component.set_editor_property("source_width", 90.0)
            light_component.set_editor_property("source_height", 90.0)
        sky = actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector())
        sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property(
            "intensity", 0.7
        )
        post = actors.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector())
        post.set_editor_property("unbound", True)
        settings = post.get_editor_property("settings")
        settings.set_editor_property("override_auto_exposure_method", True)
        settings.set_editor_property(
            "auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL
        )
        settings.set_editor_property("override_auto_exposure_bias", True)
        settings.set_editor_property("auto_exposure_bias", 0.0)
        settings.set_editor_property("override_motion_blur_amount", True)
        settings.set_editor_property("motion_blur_amount", 0.0)
        post.set_editor_property("settings", settings)
        if not unreal.EditorLevelLibrary.save_current_level():
            raise RuntimeError("failed to save v673 portrait map")
        self.borrowed = borrowed
        self.output = OUTPUT / "ururu-neutral-front.png"
        self.warmup = 240
        self.started = None
        unreal.EditorPythonScripting.set_keep_python_script_alive(True)
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def tick(self, _delta):
        if self.warmup:
            self.warmup -= 1
            return
        if self.started is None:
            self.started = time.monotonic()
            unreal.AutomationLibrary.take_high_res_screenshot(
                1200, 1200, str(self.output), self.camera
            )
            return
        if self.output.is_file() and self.output.stat().st_size > 1024:
            (OUTPUT / "report.json").write_text(json.dumps({
                "schemaVersion": 1,
                "iteration": "v673",
                "state": "captured-neutral-textured-conform-preflight",
                "neutralMesh": NEUTRAL,
                "materialDonorMesh": TEXTURED,
                "borrowedMaterials": self.borrowed,
                "bounds": {
                    "origin": [self.origin.x, self.origin.y, self.origin.z],
                    "extent": [self.extent.x, self.extent.y, self.extent.z],
                },
                "camera": {
                    "location": [
                        self.camera_location.x,
                        self.camera_location.y,
                        self.camera_location.z,
                    ],
                    "target": [self.target.x, self.target.y, self.target.z],
                    "focalLengthMm": 55.0,
                },
                "file": str(self.output),
                "sha256": hashlib.sha256(self.output.read_bytes()).hexdigest(),
                "visualValidationPending": True,
                "automaticApproval": False,
            }, indent=2) + "\n", encoding="utf-8")
            unreal.unregister_slate_post_tick_callback(self.handle)
            unreal.EditorPythonScripting.set_keep_python_script_alive(False)
            unreal.SystemLibrary.quit_editor()
        elif time.monotonic() - self.started > 180:
            raise RuntimeError("v673 portrait capture timed out")


def capture_ururu_neutral_textured_portrait_v673():
    global _driver_v673
    _driver_v673 = UruruNeutralTexturedPortraitV673()


capture_ururu_neutral_textured_portrait_v673()
