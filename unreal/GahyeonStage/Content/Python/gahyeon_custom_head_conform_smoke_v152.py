"""UE 5.8 head-only From Custom Mesh smoke using one exact in-engine camera."""

import hashlib
import json
import math
from pathlib import Path
import time

import unreal


SOURCE = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/"
    "metahuman-identity-head-v79/gahyeon-metahuman-identity-v79.obj"
)
SOURCE_SHA256 = "848c2a89ea743a2549d6e49d1f91c36d0c85bda5a508225115e668474a15c839"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v152-ue58-custom-head-conform-smoke"
)
TARGET_MAP = "/Game/Gahyeon/CharacterPipeline/v152/Preview/L_CustomHeadConformSmoke_v152"
TARGET_MESH = "/Game/Gahyeon/CharacterPipeline/v152/Input/SM_Gahyeon_CustomHeadSmoke_v152"
TARGET_CHARACTER = "/Game/Gahyeon/CharacterPipeline/v152/Character/MHC_Gahyeon_CustomHeadSmoke_v152"
PORTRAIT_SIZE = 1200
FOV_DEGREES = 40.0
_driver_v152 = None


def sha256_v152(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class CustomHeadConformDriverV152:
    def __init__(self):
        if OUTPUT.exists():
            raise RuntimeError(f"refusing to overwrite immutable v152 output: {OUTPUT}")
        if not SOURCE.is_file() or sha256_v152(SOURCE) != SOURCE_SHA256:
            raise RuntimeError("v152 smoke source lineage differs")
        for asset in (TARGET_MAP, TARGET_MESH, TARGET_CHARACTER):
            if unreal.EditorAssetLibrary.does_asset_exist(asset):
                raise RuntimeError(f"refusing to overwrite v152 asset: {asset}")
        OUTPUT.mkdir(parents=True, exist_ok=False)
        self.character = None
        self.conform_succeeded = False
        self.started = None
        self.warmup = 180
        self.portrait = OUTPUT / "target-head-front.png"
        self._build_scene()
        unreal.EditorPythonScripting.set_keep_python_script_alive(True)
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def _import_source(self):
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", str(SOURCE))
        task.set_editor_property("destination_path", "/Game/Gahyeon/CharacterPipeline/v152/Input")
        task.set_editor_property("destination_name", "SM_Gahyeon_CustomHeadSmoke_v152")
        task.set_editor_property("automated", True)
        task.set_editor_property("replace_existing", False)
        task.set_editor_property("save", True)
        options = unreal.FbxImportUI()
        options.set_editor_property("import_mesh", True)
        options.set_editor_property("import_as_skeletal", False)
        options.set_editor_property("import_materials", False)
        options.set_editor_property("import_textures", False)
        options.static_mesh_import_data.set_editor_property("combine_meshes", True)
        options.static_mesh_import_data.set_editor_property("convert_scene", False)
        options.static_mesh_import_data.set_editor_property("convert_scene_unit", False)
        task.set_editor_property("options", options)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        imported = list(task.get_editor_property("imported_object_paths"))
        if TARGET_MESH not in imported:
            raise RuntimeError(f"v152 target import mismatch: {imported}")
        mesh = unreal.EditorAssetLibrary.load_asset(TARGET_MESH)
        if mesh is None or mesh.get_class().get_name() != "StaticMesh":
            raise RuntimeError("v152 target is not a StaticMesh")
        return mesh

    def _build_scene(self):
        self.mesh = self._import_source()
        if not unreal.EditorLevelLibrary.new_level(TARGET_MAP):
            raise RuntimeError("failed to create v152 smoke map")
        self.world = unreal.EditorLevelLibrary.get_editor_world()
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        self.preview = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(), unreal.Rotator())
        self.preview.set_actor_label("CustomHeadTarget_v152")
        self.preview.static_mesh_component.set_editor_property("static_mesh", self.mesh)
        neutral = unreal.EditorAssetLibrary.load_asset("/Engine/EngineMaterials/DefaultMaterial")
        if neutral is None:
            raise RuntimeError("default neutral material unavailable")
        for index in range(len(self.mesh.static_materials)):
            self.preview.static_mesh_component.set_material(index, neutral)
        self.origin, self.extent = self.preview.get_actor_bounds(False, True)
        if self.extent.x <= 1.0 or self.extent.z <= 1.0:
            raise RuntimeError(f"implausible imported head bounds: {self.extent}")
        key = actors.spawn_actor_from_class(
            unreal.DirectionalLight, self.origin + unreal.Vector(0.0, 100.0, 100.0),
            unreal.Rotator(-25.0, -25.0, 0.0))
        key.light_component.set_editor_property("intensity", 5.0)
        sky = actors.spawn_actor_from_class(unreal.SkyLight, self.origin, unreal.Rotator())
        sky.light_component.set_editor_property("intensity", 1.5)
        self.camera = actors.spawn_actor_from_class(unreal.CameraActor, self.origin, unreal.Rotator())
        component = self.camera.camera_component
        component.set_editor_property("field_of_view", FOV_DEGREES)
        half_fov = math.radians(FOV_DEGREES * 0.5)
        distance = max(self.extent.x, self.extent.z) * 1.35 / math.tan(half_fov)
        location = self.origin + unreal.Vector(0.0, distance, 0.0)
        self.camera.set_actor_location(location, False, False)
        self.camera.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(location, self.origin), False)
        self.camera_location = location
        self.camera_rotation = self.camera.get_actor_rotation()
        if not unreal.EditorLoadingAndSavingUtils.save_map(self.world, TARGET_MAP):
            raise RuntimeError("failed to save v152 smoke map")

    def tick(self, _delta):
        if self.warmup:
            self.warmup -= 1
            return
        if self.started is None:
            self.started = time.monotonic()
            unreal.AutomationLibrary.take_high_res_screenshot(
                PORTRAIT_SIZE, PORTRAIT_SIZE, str(self.portrait), self.camera)
            return
        if self.portrait.is_file() and self.portrait.stat().st_size > 1024:
            unreal.unregister_slate_post_tick_callback(self.handle)
            try:
                self._conform()
                self.conform_succeeded = True
                self._write_receipt()
            finally:
                unreal.EditorPythonScripting.set_keep_python_script_alive(False)
            unreal.SystemLibrary.quit_editor()
        elif time.monotonic() - self.started > 180:
            unreal.unregister_slate_post_tick_callback(self.handle)
            unreal.EditorPythonScripting.set_keep_python_script_alive(False)
            raise RuntimeError("v152 exact-camera portrait capture timed out")

    def _conform(self):
        subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
        image_size, pixels = unreal.PromotedFrameUtils.get_promoted_frame_as_pixel_array_from_disk(
            str(self.portrait))
        tracked = subsystem.track_face_landmarks_from_image(pixels, image_size.x, image_size.y)
        if isinstance(tracked, tuple) and len(tracked) == 1:
            tracked = tracked[0]
        if not tracked or not hasattr(tracked, "items"):
            raise RuntimeError("v152 tracker found no face curves on exact-camera portrait")
        head_vertices, head_indices, *_ = subsystem.get_mesh_data_for_conforming(self.mesh)
        if len(head_vertices) < 1000 or len(head_indices) < 3000:
            raise RuntimeError("v152 target topology extraction is implausibly small")
        self.tracked_curve_count = len(tracked)
        self.vertex_count = len(head_vertices)
        self.triangle_count = len(head_indices) // 3
        package, name = TARGET_CHARACTER.rsplit("/", 1)
        self.character = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            asset_name=name,
            package_path=package,
            asset_class=unreal.MetaHumanCharacter,
            factory=unreal.new_object(type=unreal.MetaHumanCharacterFactoryNew),
        )
        if self.character is None:
            raise RuntimeError("failed to create v152 MetaHuman Character")
        if not subsystem.try_add_object_to_edit(self.character):
            unreal.EditorAssetLibrary.delete_asset(TARGET_CHARACTER)
            raise RuntimeError("failed to lock v152 MetaHuman Character for editing")
        try:
            params = unreal.ConformTargetParams()
            params.conform_target_mesh.target_parts_type = unreal.TargetPartsType.HEAD_ONLY
            params.conform_target_mesh.head_vertices = head_vertices
            params.conform_target_mesh.head_vertex_indices = head_indices
            params.auto_solve = True
            params.curve_tracking_points = tracked
            view = unreal.MinimalViewInfo()
            view.location = self.camera_location
            view.rotation = self.camera_rotation
            view.fov = FOV_DEGREES
            view.aspect_ratio = 1.0
            view.projection_mode = unreal.CameraProjectionMode.PERSPECTIVE
            params.camera_view_info = view
            params.image_size = image_size
            key = unreal.MetaHumanCharacterTargetMeshKey()
            key.head_mesh = self.mesh
            if not subsystem.conform_to_target_meshes(self.character, key, params):
                raise RuntimeError("UE 5.8 head-only conform_to_target_meshes failed")
            subsystem.commit_posed_state_as_a_pose(self.character, key)
            if not unreal.EditorAssetLibrary.save_asset(TARGET_CHARACTER, only_if_is_dirty=True):
                raise RuntimeError("failed to save v152 conformed character")
        except Exception:
            unreal.EditorAssetLibrary.delete_asset(TARGET_CHARACTER)
            raise
        finally:
            if subsystem.is_object_added_for_editing(self.character):
                subsystem.remove_object_to_edit(self.character)

    def _write_receipt(self):
        receipt = {
            "schemaVersion": 1,
            "iteration": "v152",
            "state": "technical-smoke-conformed-awaiting-visual-rejection",
            "engine": "5.8",
            "source": {"path": str(SOURCE), "sha256": SOURCE_SHA256,
                       "role": "historical-low-quality-technical-fixture"},
            "targetMesh": TARGET_MESH,
            "targetCharacter": TARGET_CHARACTER,
            "map": TARGET_MAP,
            "portrait": {"path": str(self.portrait), "sha256": sha256_v152(self.portrait),
                         "size": [PORTRAIT_SIZE, PORTRAIT_SIZE]},
            "camera": {"location": [self.camera_location.x, self.camera_location.y,
                                      self.camera_location.z],
                       "rotation": [self.camera_rotation.pitch, self.camera_rotation.yaw,
                                    self.camera_rotation.roll],
                       "fovDegrees": FOV_DEGREES, "aspectRatio": 1.0,
                       "sameCameraUsedForCaptureAndConform": True},
            "targetTopology": {"vertices": self.vertex_count, "triangles": self.triangle_count},
            "trackedCurveCount": self.tracked_curve_count,
            "hypothesis": "UE-internal portrait capture removes camera mismatch from the custom-head conform path.",
            "identityCandidate": False,
            "automaticApproval": False,
            "productionReady": False,
        }
        (OUTPUT / "conform-receipt.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def start_custom_head_conform_v152():
    global _driver_v152
    _driver_v152 = CustomHeadConformDriverV152()


start_custom_head_conform_v152()
