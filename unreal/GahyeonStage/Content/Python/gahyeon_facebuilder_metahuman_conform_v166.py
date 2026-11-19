"""UE 5.8 FaceBuilder head import, adaptive portrait selection and conform.

The package directory is supplied through GAHYEON_FACEBUILDER_PACKAGE. Four
cardinal exact-camera portraits are rendered and scored with UE's face tracker;
the best valid portrait drives Custom Mesh conform. No guessed source axis is
accepted and no prior iteration is overwritten.
"""

import hashlib
import json
import math
import os
from pathlib import Path
import time
import traceback

import unreal


ITERATION = "v166"
PACKAGE_DIR = Path(os.environ.get("GAHYEON_FACEBUILDER_PACKAGE", ""))
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v166-ue58-facebuilder-metahuman-conform"
)
ASSET_ROOT = "/Game/Gahyeon/CharacterPipeline/v166"
TARGET_MAP = f"{ASSET_ROOT}/Preview/L_FaceBuilderConform_v166"
TARGET_MESH = f"{ASSET_ROOT}/Input/SM_Gahyeon_FaceBuilder_v166"
TARGET_CHARACTER = f"{ASSET_ROOT}/Character/MHC_Gahyeon_FaceBuilder_v166"
PORTRAIT_SIZE = 1200
FOV_DEGREES = 35.0
_driver_v166 = None


def sha256_v166(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class AdaptiveCustomHeadConformDriverV166:
    def __init__(self):
        self.manifest = self._validate_input()
        if OUTPUT.exists():
            raise RuntimeError(f"refusing to overwrite immutable output: {OUTPUT}")
        for asset in (TARGET_MAP, TARGET_MESH, TARGET_CHARACTER):
            if unreal.EditorAssetLibrary.does_asset_exist(asset):
                raise RuntimeError(f"refusing to overwrite immutable asset: {asset}")
        OUTPUT.mkdir(parents=True, exist_ok=False)
        self.capture_index = 0
        self.capture_started = None
        self.warmup = 180
        self.portraits = []
        self.failure = None
        try:
            self._build_scene()
        except Exception as error:
            self._write_failure(error)
            raise
        unreal.EditorPythonScripting.set_keep_python_script_alive(True)
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def _validate_input(self):
        if not PACKAGE_DIR.is_dir():
            raise RuntimeError("GAHYEON_FACEBUILDER_PACKAGE must name a normalized v163 package")
        manifest_path = PACKAGE_DIR / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("iteration") != "v163":
            raise RuntimeError("expected normalized FaceBuilder conform package v163")
        claims = manifest.get("claims", {})
        if claims.get("identityApproved") is not False or claims.get("metaHumanConformed") is not False:
            raise RuntimeError("input package has invalid pre-conform claims")
        files = {entry["uri"]: entry for entry in manifest.get("files", [])}
        normalization = manifest.get("normalization", {})
        if (normalization.get("identityShapeChanged") is not False
                or not 20.0 <= normalization.get("measuredHeadHeightCm", 0.0) <= 40.0):
            raise RuntimeError("v163 physical normalization contract is invalid")
        required = "gahyeon-facebuilder-normalized-v163.fbx"
        if required not in files:
            raise RuntimeError("v163 package lacks the normalized FBX payload")
        source = PACKAGE_DIR / required
        entry = files[required]
        if (not source.is_file() or source.stat().st_size != entry["bytes"]
                or sha256_v166(source) != entry["sha256"]):
            raise RuntimeError("v163 FBX lineage mismatch")
        self.source = source
        self.source_sha256 = entry["sha256"]
        return manifest

    def _import_source(self):
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", str(self.source))
        task.set_editor_property("destination_path", f"{ASSET_ROOT}/Input")
        task.set_editor_property("destination_name", "SM_Gahyeon_FaceBuilder_v166")
        task.set_editor_property("automated", True)
        task.set_editor_property("replace_existing", False)
        task.set_editor_property("save", True)
        options = unreal.FbxImportUI()
        options.set_editor_property("import_mesh", True)
        options.set_editor_property("import_as_skeletal", False)
        options.set_editor_property("import_materials", False)
        options.set_editor_property("import_textures", False)
        options.static_mesh_import_data.set_editor_property("combine_meshes", True)
        options.static_mesh_import_data.set_editor_property("convert_scene", True)
        options.static_mesh_import_data.set_editor_property("convert_scene_unit", True)
        task.set_editor_property("options", options)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        imported = [path.split(".", 1)[0] for path in task.get_editor_property("imported_object_paths")]
        if TARGET_MESH not in imported:
            raise RuntimeError(f"target import mismatch: {imported}")
        mesh = unreal.EditorAssetLibrary.load_asset(TARGET_MESH)
        if mesh is None or mesh.get_class().get_name() != "StaticMesh":
            raise RuntimeError("FaceBuilder target is not a StaticMesh")
        return mesh

    def _build_scene(self):
        self.mesh = self._import_source()
        if not unreal.EditorLevelLibrary.new_level(TARGET_MAP):
            raise RuntimeError("failed to create v166 conform map")
        self.world = unreal.EditorLevelLibrary.get_editor_world()
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        self.preview = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(), unreal.Rotator())
        self.preview.set_actor_label("FaceBuilderTarget_v166")
        self.preview.static_mesh_component.set_editor_property("static_mesh", self.mesh)
        neutral = unreal.EditorAssetLibrary.load_asset("/Engine/EngineMaterials/DefaultMaterial")
        if neutral is None:
            raise RuntimeError("default neutral material unavailable")
        for index in range(len(self.mesh.static_materials)):
            self.preview.static_mesh_component.set_material(index, neutral)
        self.origin, self.extent = self.preview.get_actor_bounds(False, True)
        if min(self.extent.x, self.extent.y, self.extent.z) <= 0.1:
            raise RuntimeError(f"implausible imported FaceBuilder bounds: {self.extent}")
        key = actors.spawn_actor_from_class(
            unreal.DirectionalLight, self.origin + unreal.Vector(0.0, 100.0, 100.0),
            unreal.Rotator(-25.0, -25.0, 0.0))
        key.light_component.set_editor_property("intensity", 5.0)
        sky = actors.spawn_actor_from_class(unreal.SkyLight, self.origin, unreal.Rotator())
        sky.light_component.set_editor_property("intensity", 1.5)

        half_fov = math.radians(FOV_DEGREES * 0.5)
        distance = max(self.extent.x, self.extent.y, self.extent.z) * 1.5 / math.tan(half_fov)
        directions = (
            ("plus-x", unreal.Vector(distance, 0.0, 0.0)),
            ("minus-x", unreal.Vector(-distance, 0.0, 0.0)),
            ("plus-y", unreal.Vector(0.0, distance, 0.0)),
            ("minus-y", unreal.Vector(0.0, -distance, 0.0)),
        )
        self.cameras = []
        for name, offset in directions:
            camera = actors.spawn_actor_from_class(unreal.CameraActor, self.origin, unreal.Rotator())
            camera.set_actor_label(f"FaceBuilder_{name}_v166")
            camera.camera_component.set_editor_property("field_of_view", FOV_DEGREES)
            location = self.origin + offset
            camera.set_actor_location(location, False, False)
            camera.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(location, self.origin), False)
            self.cameras.append((name, camera))
        if not unreal.EditorLoadingAndSavingUtils.save_map(self.world, TARGET_MAP):
            raise RuntimeError("failed to save v166 conform map")

    def tick(self, _delta):
        try:
            if self.warmup:
                self.warmup -= 1
                return
            if self.capture_index < len(self.cameras):
                name, camera = self.cameras[self.capture_index]
                portrait = OUTPUT / f"axis-{name}.png"
                if self.capture_started is None:
                    self.capture_started = time.monotonic()
                    unreal.AutomationLibrary.take_high_res_screenshot(
                        PORTRAIT_SIZE, PORTRAIT_SIZE, str(portrait), camera)
                    return
                if portrait.is_file() and portrait.stat().st_size > 1024:
                    self.portraits.append((name, camera, portrait))
                    self.capture_index += 1
                    self.capture_started = None
                    self.warmup = 30
                    return
                if time.monotonic() - self.capture_started > 180:
                    raise RuntimeError(f"portrait capture timed out: {name}")
                return
            self._finish()
        except Exception as error:
            self._shutdown()
            self._write_failure(error)
            unreal.log_error(traceback.format_exc())
            unreal.SystemLibrary.quit_editor()

    def _track_portraits(self, subsystem):
        scored = []
        for name, camera, path in self.portraits:
            image_size, pixels = unreal.PromotedFrameUtils.get_promoted_frame_as_pixel_array_from_disk(
                str(path))
            tracked = subsystem.track_face_landmarks_from_image(pixels, image_size.x, image_size.y)
            if isinstance(tracked, tuple) and len(tracked) == 1:
                tracked = tracked[0]
            count = len(tracked) if tracked and hasattr(tracked, "items") else 0
            scored.append((count, name, camera, path, image_size, tracked if count else None))
        scored.sort(key=lambda item: item[0], reverse=True)
        if not scored or scored[0][0] == 0:
            raise RuntimeError("UE face tracker found no valid frontal FaceBuilder portrait")
        return scored

    def _finish(self):
        self._shutdown()
        subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
        scored = self._track_portraits(subsystem)
        count, name, camera, portrait, image_size, tracked = scored[0]
        head_vertices, head_indices, *_ = subsystem.get_mesh_data_for_conforming(self.mesh)
        if len(head_vertices) < 1_000 or len(head_indices) < 3_000:
            raise RuntimeError("FaceBuilder target topology extraction is implausibly small")
        package, asset_name = TARGET_CHARACTER.rsplit("/", 1)
        character = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            asset_name=asset_name,
            package_path=package,
            asset_class=unreal.MetaHumanCharacter,
            factory=unreal.new_object(type=unreal.MetaHumanCharacterFactoryNew),
        )
        if character is None or not subsystem.try_add_object_to_edit(character):
            if character is not None:
                unreal.EditorAssetLibrary.delete_asset(TARGET_CHARACTER)
            raise RuntimeError("failed to create or lock v166 MetaHuman Character")
        conformed = False
        try:
            params = unreal.ConformTargetParams()
            params.conform_target_mesh.target_parts_type = unreal.TargetPartsType.HEAD_ONLY
            params.conform_target_mesh.head_vertices = head_vertices
            params.conform_target_mesh.head_vertex_indices = head_indices
            params.auto_solve = True
            params.curve_tracking_points = tracked
            view = unreal.MinimalViewInfo()
            view.location = camera.get_actor_location()
            view.rotation = camera.get_actor_rotation()
            view.fov = FOV_DEGREES
            view.aspect_ratio = float(image_size.x) / float(image_size.y)
            view.projection_mode = unreal.CameraProjectionMode.PERSPECTIVE
            params.camera_view_info = view
            params.image_size = image_size
            key = unreal.MetaHumanCharacterTargetMeshKey()
            key.head_mesh = self.mesh
            if not subsystem.conform_to_target_meshes(character, key, params):
                raise RuntimeError("UE 5.8 conform_to_target_meshes failed")
            subsystem.commit_posed_state_as_a_pose(character, key)
            if not unreal.EditorAssetLibrary.save_asset(TARGET_CHARACTER, only_if_is_dirty=True):
                raise RuntimeError("failed to save v166 conformed MetaHuman")
            conformed = True
        finally:
            if subsystem.is_object_added_for_editing(character):
                subsystem.remove_object_to_edit(character)
            if not conformed:
                unreal.EditorAssetLibrary.delete_asset(TARGET_CHARACTER)
        receipt = {
            "schemaVersion": 1,
            "iteration": ITERATION,
            "state": "metahuman-conformed-awaiting-fixed-camera-identity-review",
            "engine": "5.8",
            "source": {"path": str(self.source), "sha256": self.source_sha256},
            "targetMesh": TARGET_MESH,
            "targetCharacter": TARGET_CHARACTER,
            "map": TARGET_MAP,
            "axisPortraitScores": [
                {"axis": item[1], "trackedCurveCount": item[0], "path": str(item[3]),
                 "sha256": sha256_v166(item[3])}
                for item in scored
            ],
            "selectedPortrait": {"axis": name, "trackedCurveCount": count,
                                 "path": str(portrait), "sameCameraUsedForConform": True},
            "targetTopology": {"vertices": len(head_vertices),
                               "triangles": len(head_indices) // 3},
            "identityApproved": False,
            "automaticApproval": False,
            "productionReady": False,
        }
        (OUTPUT / "conform-receipt.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        unreal.SystemLibrary.quit_editor()

    def _shutdown(self):
        if hasattr(self, "handle"):
            unreal.unregister_slate_post_tick_callback(self.handle)
            del self.handle
        unreal.EditorPythonScripting.set_keep_python_script_alive(False)

    def _write_failure(self, error):
        if not OUTPUT.exists():
            OUTPUT.mkdir(parents=True, exist_ok=True)
        payload = {
            "schemaVersion": 1,
            "iteration": ITERATION,
            "state": "failed-closed",
            "errorType": type(error).__name__,
            "error": str(error),
            "identityApproved": False,
            "productionReady": False,
        }
        (OUTPUT / "failure-receipt.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def start_adaptive_custom_head_conform_v166():
    global _driver_v166
    _driver_v166 = AdaptiveCustomHeadConformDriverV166()


start_adaptive_custom_head_conform_v166()
