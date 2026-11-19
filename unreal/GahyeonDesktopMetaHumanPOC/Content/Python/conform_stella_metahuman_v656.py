"""Conform the immutable Stella/Lily neutral head into a UE 5.8 MetaHuman draft."""

import hashlib
import json
import math
from pathlib import Path
import time

import unreal


SOURCE = Path(
    "/Users/ze/work/gahyeonbot/artifacts/"
    "living-character-poc-v650-neutral-head-conform-inputs/"
    "stella-lily-neutral-head-v650.obj"
)
SOURCE_SHA256 = "85c77ea09acc1be198722663e460847ead3ae489602b1ff93c048ee6e6c5129e"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/"
    "living-character-poc-v656-stella-metahuman-conform"
)
TARGET_MESH = "/Game/LivingCharacterPOC/v651/Input/SM_StellaLily_NeutralHead_v651"
PREVIEW_MESH = "/Game/LivingCharacterPOC/v558/Characters/StellaLilyTextured/StellaLily_PreviewReady_v556"
TARGET_MAP = "/Game/LivingCharacterPOC/v656/Preview/L_StellaNeutralHeadTracking_v656"
TARGET_CHARACTER = "/Game/LivingCharacterPOC/v656/Character/MHC_StellaLily_Draft_v656"
PORTRAIT_SIZE = 1200
FOV_DEGREES = 36.0
_driver_v656 = None


def sha256_file_v656(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class StellaMetaHumanConformDriverV656:
    def __init__(self):
        if OUTPUT.exists():
            raise RuntimeError(f"refusing to overwrite immutable v656 output: {OUTPUT}")
        if not SOURCE.is_file() or sha256_file_v656(SOURCE) != SOURCE_SHA256:
            raise RuntimeError("sealed Stella v650 source lineage differs")
        if not unreal.EditorAssetLibrary.does_asset_exist(TARGET_MESH):
            raise RuntimeError(f"sealed v651 target mesh is missing: {TARGET_MESH}")
        for asset in (TARGET_MAP, TARGET_CHARACTER):
            if unreal.EditorAssetLibrary.does_asset_exist(asset):
                raise RuntimeError(f"refusing to overwrite immutable v656 asset: {asset}")
        OUTPUT.mkdir(parents=True, exist_ok=False)
        self.character = None
        self.started = None
        self.warmup = 180
        self.portrait = OUTPUT / "stella-neutral-head-front.png"
        self._build_scene()
        unreal.EditorPythonScripting.set_keep_python_script_alive(True)
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def _build_scene(self):
        self.mesh = unreal.load_asset(TARGET_MESH)
        if self.mesh is None or self.mesh.get_class().get_name() != "StaticMesh":
            raise RuntimeError("v651 Stella target is not a StaticMesh")
        preview_mesh = unreal.load_asset(PREVIEW_MESH)
        if preview_mesh is None or preview_mesh.get_class().get_name() != "SkeletalMesh":
            raise RuntimeError("validated textured Stella preview is unavailable")
        if not unreal.EditorLevelLibrary.new_level(TARGET_MAP):
            raise RuntimeError("failed to create v656 tracking map")
        self.world = unreal.EditorLevelLibrary.get_editor_world()
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

        measure = actors.spawn_actor_from_class(
            unreal.StaticMeshActor, unreal.Vector(), unreal.Rotator()
        )
        measure.static_mesh_component.set_editor_property("static_mesh", self.mesh)
        measure.set_actor_rotation(
            unreal.Rotator(roll=90.0, pitch=0.0, yaw=0.0), False
        )
        self.origin, self.extent = measure.get_actor_bounds(False, True)
        if not (5.0 <= self.extent.x <= 15.0 and 7.0 <= self.extent.z <= 20.0):
            raise RuntimeError(f"implausible oriented Stella head bounds: {self.extent}")
        actors.destroy_actor(measure)

        self.preview = actors.spawn_actor_from_class(
            unreal.SkeletalMeshActor,
            unreal.Vector(),
            unreal.Rotator(roll=0.0, pitch=0.0, yaw=0.0),
        )
        self.preview.set_actor_label("StellaTexturedTrackingPreview_v656")
        self.preview.get_component_by_class(
            unreal.SkeletalMeshComponent
        ).set_editor_property("skeletal_mesh_asset", preview_mesh)
        _, preview_extent = self.preview.get_actor_bounds(False, True)
        if not 140.0 <= preview_extent.z * 2.0 <= 190.0:
            raise RuntimeError(f"implausible Stella tracking-preview height: {preview_extent}")

        for offset, intensity in (
            (unreal.Vector(-45.0, 65.0, 35.0), 8500.0),
            (unreal.Vector(45.0, 60.0, 20.0), 7000.0),
            (unreal.Vector(0.0, -45.0, 30.0), 5500.0),
        ):
            light_location = self.origin + offset
            light = actors.spawn_actor_from_class(
                unreal.RectLight,
                light_location,
                unreal.MathLibrary.find_look_at_rotation(light_location, self.origin),
            )
            light_component = light.get_component_by_class(unreal.RectLightComponent)
            light_component.set_editor_property("intensity", intensity)
            light_component.set_editor_property("source_width", 55.0)
            light_component.set_editor_property("source_height", 55.0)
        sky = actors.spawn_actor_from_class(
            unreal.SkyLight, self.origin, unreal.Rotator()
        )
        sky.light_component.set_editor_property("intensity", 1.2)
        post = actors.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector())
        post.set_editor_property("unbound", True)
        settings = post.get_editor_property("settings")
        settings.set_editor_property("override_auto_exposure_method", True)
        settings.set_editor_property(
            "auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL
        )
        settings.set_editor_property("override_auto_exposure_bias", True)
        settings.set_editor_property("auto_exposure_bias", 1.0)
        settings.set_editor_property("override_motion_blur_amount", True)
        settings.set_editor_property("motion_blur_amount", 0.0)
        post.set_editor_property("settings", settings)

        self.camera = actors.spawn_actor_from_class(
            unreal.CameraActor, self.origin, unreal.Rotator()
        )
        component = self.camera.camera_component
        component.set_editor_property("field_of_view", FOV_DEGREES)
        half_fov = math.radians(FOV_DEGREES * 0.5)
        distance = max(self.extent.x, self.extent.z) * 1.42 / math.tan(half_fov)
        location = self.origin + unreal.Vector(0.0, distance, 0.0)
        self.camera.set_actor_location(location, False, False)
        self.camera.set_actor_rotation(
            unreal.MathLibrary.find_look_at_rotation(location, self.origin), False
        )
        self.camera_location = location
        self.camera_rotation = self.camera.get_actor_rotation()
        if not unreal.EditorLoadingAndSavingUtils.save_map(self.world, TARGET_MAP):
            raise RuntimeError("failed to save v656 tracking map")

    def tick(self, _delta):
        if self.warmup:
            self.warmup -= 1
            return
        if self.started is None:
            self.started = time.monotonic()
            unreal.AutomationLibrary.take_high_res_screenshot(
                PORTRAIT_SIZE, PORTRAIT_SIZE, str(self.portrait), self.camera
            )
            return
        if self.portrait.is_file() and self.portrait.stat().st_size > 1024:
            unreal.unregister_slate_post_tick_callback(self.handle)
            try:
                self._conform()
                self._write_receipt()
            finally:
                unreal.EditorPythonScripting.set_keep_python_script_alive(False)
            unreal.SystemLibrary.quit_editor()
        elif time.monotonic() - self.started > 180:
            unreal.unregister_slate_post_tick_callback(self.handle)
            unreal.EditorPythonScripting.set_keep_python_script_alive(False)
            raise RuntimeError("v656 portrait capture timed out")

    def _conform(self):
        subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
        image_size, pixels = unreal.PromotedFrameUtils.get_promoted_frame_as_pixel_array_from_disk(
            str(self.portrait)
        )
        self.image_size = image_size
        tracked = subsystem.track_face_landmarks_from_image(
            pixels, image_size.x, image_size.y
        )
        if isinstance(tracked, tuple) and len(tracked) == 1:
            tracked = tracked[0]
        if not tracked or not hasattr(tracked, "items"):
            raise RuntimeError("UE face tracker found no curves on Stella neutral portrait")
        head_vertices, head_indices, *_ = subsystem.get_mesh_data_for_conforming(self.mesh)
        if len(head_vertices) < 1000 or len(head_indices) < 3000:
            raise RuntimeError("Stella target topology extraction is implausibly small")
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
            raise RuntimeError("failed to create Stella MetaHuman Character draft")
        if not subsystem.try_add_object_to_edit(self.character):
            unreal.EditorAssetLibrary.delete_asset(TARGET_CHARACTER)
            raise RuntimeError("failed to lock Stella MetaHuman Character for editing")
        conformed = False
        try:
            params = unreal.ConformTargetParams()
            params.conform_target_mesh.target_parts_type = unreal.TargetPartsType.HEAD_ONLY
            params.conform_target_mesh.head_vertices = head_vertices
            params.conform_target_mesh.head_vertex_indices = head_indices
            params.auto_solve = True
            params.body_conform_solve_settings.pipeline_name = "head_only"
            params.curve_tracking_points = tracked
            view = unreal.MinimalViewInfo()
            view.location = self.camera_location
            view.rotation = self.camera_rotation
            view.fov = FOV_DEGREES
            view.aspect_ratio = float(image_size.x) / float(image_size.y)
            view.projection_mode = unreal.CameraProjectionMode.PERSPECTIVE
            params.camera_view_info = view
            params.image_size = image_size
            key = unreal.MetaHumanCharacterTargetMeshKey()
            key.head_mesh = self.mesh
            if not subsystem.conform_to_target_meshes(self.character, key, params):
                raise RuntimeError("UE 5.8 Stella head conform_to_target_meshes failed")
            subsystem.commit_posed_state_as_a_pose(self.character, key)
            if not unreal.EditorAssetLibrary.save_asset(
                TARGET_CHARACTER, only_if_is_dirty=True
            ):
                raise RuntimeError("failed to save Stella MetaHuman draft")
            conformed = True
        finally:
            if subsystem.is_object_added_for_editing(self.character):
                subsystem.remove_object_to_edit(self.character)
            if not conformed:
                unreal.EditorAssetLibrary.delete_asset(TARGET_CHARACTER)

    def _write_receipt(self):
        payload = {
            "schemaVersion": 1,
            "iteration": "v656",
            "state": "draft-conformed-awaiting-fixed-camera-surface-qa",
            "engine": "5.8",
            "characterId": "stella-lily",
            "source": {"path": str(SOURCE), "sha256": SOURCE_SHA256},
            "targetMesh": TARGET_MESH,
            "trackingPreviewMesh": PREVIEW_MESH,
            "targetCharacter": TARGET_CHARACTER,
            "trackingMap": TARGET_MAP,
            "portrait": {
                "path": str(self.portrait),
                "sha256": sha256_file_v656(self.portrait),
                "size": [self.image_size.x, self.image_size.y],
            },
            "camera": {
                "locationCm": [
                    self.camera_location.x,
                    self.camera_location.y,
                    self.camera_location.z,
                ],
                "rotationDegrees": [
                    self.camera_rotation.pitch,
                    self.camera_rotation.yaw,
                    self.camera_rotation.roll,
                ],
                "fovDegrees": FOV_DEGREES,
                "sameCameraUsedForCaptureAndConform": True,
            },
            "targetTopology": {
                "vertices": self.vertex_count,
                "triangles": self.triangle_count,
            },
            "trackedCurveCount": self.tracked_curve_count,
            "hypothesis": (
                "Stella's sealed neutral head can recover its shape inside MetaHuman "
                "production topology without modifying the donor body asset."
            ),
            "actualResult": "UE 5.8 head-only conform completed; visual surface QA remains required.",
            "decision": "retain as draft until fixed-camera conformed-surface comparison",
            "automaticApproval": False,
            "identityApproved": False,
            "productionReady": False,
        }
        (OUTPUT / "conform-receipt.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def start_stella_metahuman_conform_v656():
    global _driver_v656
    _driver_v656 = StellaMetaHumanConformDriverV656()


start_stella_metahuman_conform_v656()



