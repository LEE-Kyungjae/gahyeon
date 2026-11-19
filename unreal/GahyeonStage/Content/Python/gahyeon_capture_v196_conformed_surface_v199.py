"""Render five immutable clay views of v196's actual conformed MetaHuman surface."""

import hashlib
import json
import math
import os
from pathlib import Path
import time
import traceback

import unreal


ITERATION = os.environ.get("GAHYEON_SURFACE_QA_ITERATION", "v199")
CHARACTER = os.environ.get(
    "GAHYEON_SURFACE_QA_CHARACTER",
    "/Game/Gahyeon/CharacterPipeline/v196/Character/MHC_Gahyeon_KeenTools_Cm_v196",
)
SOURCE_CONFORM_RECEIPT = os.environ.get(
    "GAHYEON_SURFACE_QA_CONFORM_RECEIPT",
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v196-ue58-keentools-centimetre-conform/conform-receipt.json",
)
MAP = f"/Game/Gahyeon/CharacterPipeline/{ITERATION}/Preview/L_ConformedSurfaceQA_{ITERATION}"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    f"{ITERATION}-metahuman-conformed-surface-qa"
)
VIEWS = (("front", 0.0), ("left-45", -45.0), ("right-45", 45.0),
         ("left-profile", -90.0), ("right-profile", 90.0))
_driver_v199 = None


def sha256_v199(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class ConformedSurfaceCaptureDriverV199:
    def __init__(self):
        if OUTPUT.exists() or unreal.EditorAssetLibrary.does_asset_exist(MAP):
            raise RuntimeError("refusing to overwrite immutable v199 QA")
        OUTPUT.mkdir(parents=True, exist_ok=False)
        self.character = unreal.load_asset(CHARACTER)
        self.subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
        if self.character is None or not self.subsystem.try_add_object_to_edit(self.character):
            raise RuntimeError("failed to initialize v196 conformed preview")
        self.editing = True
        try:
            self._build_scene()
        except Exception as error:
            self._write_failure(error)
            self._release()
            raise
        self.index = 0
        self.started = None
        self.warmup = 180
        unreal.EditorPythonScripting.set_keep_python_script_alive(True)
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def _transient_meshes(self):
        result = {}
        for mesh in unreal.ObjectIterator(unreal.SkeletalMesh):
            path = mesh.get_path_name()
            if "MetaHumanCharacterEditorSubsystem" not in path:
                continue
            if mesh.get_name().startswith("FaceMesh"):
                result["face"] = mesh
            elif mesh.get_name().startswith("BodyMesh"):
                result["body"] = mesh
        if set(result) != {"face", "body"}:
            raise RuntimeError(f"expected transient face/body meshes, got {result}")
        return result

    def _build_scene(self):
        meshes = self._transient_meshes()
        if not unreal.EditorLevelLibrary.new_level(MAP):
            raise RuntimeError("failed to create v199 QA map")
        self.world = unreal.EditorLevelLibrary.get_editor_world()
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        clay = unreal.load_asset("/Engine/EngineMaterials/DefaultMaterial")
        if clay is None:
            raise RuntimeError("neutral clay material unavailable")
        self.mesh_records = []
        for role in ("face",):
            actor = actors.spawn_actor_from_class(
                unreal.SkeletalMeshActor, unreal.Vector(), unreal.Rotator())
            actor.set_actor_label(f"Conformed_{role.title()}_v199")
            component = actor.get_component_by_class(unreal.SkeletalMeshComponent)
            component.set_editor_property("skeletal_mesh_asset", meshes[role])
            for material_index in range(len(meshes[role].materials)):
                component.set_material(material_index, clay)
            bounds = meshes[role].get_imported_bounds()
            self.mesh_records.append({
                "role": role,
                "path": meshes[role].get_path_name(),
                "origin": [bounds.origin.x, bounds.origin.y, bounds.origin.z],
                "extent": [bounds.box_extent.x, bounds.box_extent.y, bounds.box_extent.z],
            })
        face = meshes["face"].get_imported_bounds()
        self.target = face.origin
        face_radius = max(face.box_extent.x, face.box_extent.y, face.box_extent.z)
        half_fov = math.radians(28.0 * 0.5)
        distance = face_radius * 1.38 / math.tan(half_fov)
        self.cameras = []
        for name, angle in VIEWS:
            radians = math.radians(angle)
            offset = unreal.Vector(
                -math.sin(radians) * distance,
                math.cos(radians) * distance,
                0.0,
            )
            camera = actors.spawn_actor_from_class(
                unreal.CameraActor, self.target, unreal.Rotator())
            camera.set_actor_label(f"ConformedSurface_{name}_v199")
            camera.camera_component.set_editor_property("field_of_view", 28.0)
            camera.camera_component.set_editor_property("constrain_aspect_ratio", True)
            camera.camera_component.set_editor_property("aspect_ratio", 1440.0 / 2560.0)
            location = self.target + offset
            camera.set_actor_location(location, False, False)
            camera.set_actor_rotation(
                unreal.MathLibrary.find_look_at_rotation(location, self.target), False)
            self.cameras.append((name, camera))
        for yaw, intensity in ((-35.0, 4.0), (50.0, 2.0), (180.0, 2.5)):
            light = actors.spawn_actor_from_class(
                unreal.DirectionalLight, self.target, unreal.Rotator(-30.0, yaw, 0.0))
            component = light.get_component_by_class(unreal.DirectionalLightComponent)
            component.set_editor_property("intensity", intensity)
            component.set_editor_property("cast_shadows", yaw == -35.0)
        sky = actors.spawn_actor_from_class(unreal.SkyLight, self.target, unreal.Rotator())
        sky.light_component.set_editor_property("intensity", 1.2)
        if not unreal.EditorLoadingAndSavingUtils.save_map(self.world, MAP):
            raise RuntimeError("failed to save v199 QA map")

    def tick(self, _delta):
        try:
            if self.warmup:
                self.warmup -= 1
                return
            if self.index < len(self.cameras):
                name, camera = self.cameras[self.index]
                output = OUTPUT / f"{name}.png"
                if self.started is None:
                    self.started = time.monotonic()
                    unreal.AutomationLibrary.take_high_res_screenshot(
                        1440, 2560, str(output), camera)
                    return
                if output.is_file() and output.stat().st_size > 4096:
                    self.index += 1
                    self.started = None
                    self.warmup = 30
                    return
                if time.monotonic() - self.started > 180:
                    raise RuntimeError(f"v199 screenshot timed out: {name}")
                return
            self._finish()
        except Exception as error:
            self._write_failure(error)
            unreal.log_error(traceback.format_exc())
            self._shutdown()
            unreal.SystemLibrary.quit_editor()

    def _finish(self):
        images = []
        for name, _camera in self.cameras:
            path = OUTPUT / f"{name}.png"
            images.append({"view": name, "path": str(path), "sha256": sha256_v199(path),
                           "bytes": path.stat().st_size})
        (OUTPUT / "render-receipt.json").write_text(json.dumps({
            "schemaVersion": 1,
            "iteration": ITERATION,
            "state": "five-view-conformed-clay-awaiting-human-identity-review",
            "sourceCharacter": CHARACTER,
            "sourceConformReceipt": SOURCE_CONFORM_RECEIPT,
            "map": MAP,
            "meshRecords": self.mesh_records,
            "camera": {"fovDegrees": 28.0, "requestedResolution": [1440, 2560]},
            "images": images,
            "identityApproved": False,
            "automaticApproval": False,
            "productionReady": False,
        }, indent=2) + "\n", encoding="utf-8")
        self._shutdown()
        unreal.log(f"Gahyeon v199 five-view conformed surface QA complete: {OUTPUT}")
        unreal.SystemLibrary.quit_editor()

    def _write_failure(self, error):
        (OUTPUT / "failure-receipt.json").write_text(json.dumps({
            "schemaVersion": 1, "iteration": ITERATION, "state": "failed",
            "errorType": type(error).__name__, "error": str(error),
            "automaticApproval": False, "productionReady": False,
        }, indent=2) + "\n", encoding="utf-8")

    def _release(self):
        if getattr(self, "editing", False):
            if self.subsystem.is_object_added_for_editing(self.character):
                self.subsystem.remove_object_to_edit(self.character)
            self.editing = False

    def _shutdown(self):
        handle = getattr(self, "handle", None)
        if handle is not None:
            unreal.unregister_slate_post_tick_callback(handle)
            self.handle = None
        self._release()
        unreal.EditorPythonScripting.set_keep_python_script_alive(False)


def start_conformed_surface_capture_v199():
    global _driver_v199
    _driver_v199 = ConformedSurfaceCaptureDriverV199()


start_conformed_surface_capture_v199()
