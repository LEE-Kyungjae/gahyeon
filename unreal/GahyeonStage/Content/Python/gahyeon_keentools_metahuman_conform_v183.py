"""UE 5.8 KeenTools head import, adaptive portrait selection and conform.

The package directory is supplied through GAHYEON_KEENTOOLS_PACKAGE. Four
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


ITERATION = "v183"
PACKAGE_DIR = Path(os.environ.get("GAHYEON_KEENTOOLS_PACKAGE", ""))
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v183-ue58-keentools-metahuman-conform"
)
ASSET_ROOT = "/Game/Gahyeon/CharacterPipeline/v183"
TARGET_MAP = f"{ASSET_ROOT}/Preview/L_KeenToolsConform_v183"
TARGET_MESH = f"{ASSET_ROOT}/Input/SM_Gahyeon_KeenTools_v183"
TARGET_CHARACTER = f"{ASSET_ROOT}/Character/MHC_Gahyeon_KeenTools_v183"
PORTRAIT_SIZE = 1200
FOV_DEGREES = 35.0
_driver_v183 = None


def sha256_v183(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class AdaptiveCustomHeadConformDriverV183:
    def __init__(self):
        self.manifest = self._validate_input()
        if OUTPUT.exists():
            raise RuntimeError(f"refusing to overwrite immutable output: {OUTPUT}")
        for asset in (TARGET_MAP, TARGET_MESH, TARGET_CHARACTER):
            if unreal.EditorAssetLibrary.does_asset_exist(asset):
                raise RuntimeError(f"refusing to overwrite immutable asset: {asset}")
        OUTPUT.mkdir(parents=True, exist_ok=False)
        self.capture_index = 0
        self.target_offset_z_cm = float(os.environ.get("GAHYEON_HEAD_TARGET_OFFSET_Z_CM", "0"))
        self.rotate_target_yaw_180 = os.environ.get("GAHYEON_ROTATE_TARGET_YAW_180") == "1"
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
            raise RuntimeError("GAHYEON_KEENTOOLS_PACKAGE must name the sealed v181 package")
        manifest_path = PACKAGE_DIR / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("iteration") != "v181":
            raise RuntimeError("expected sealed KeenTools conform package v181")
        claims = manifest.get("claims", {})
        if (claims.get("identityApproved") is not False
                or claims.get("metaHumanConformed") is not False
                or claims.get("productionTopology") is not False
                or claims.get("conformExperimentAuthorizedByUser") is not True):
            raise RuntimeError("input package has invalid pre-conform claims")
        files = {entry["uri"]: entry for entry in manifest.get("files", [])}
        topology = manifest.get("topology", {})
        dimensions = topology.get("dimensionsCm", [])
        if (topology.get("vertices") != 22_808
                or topology.get("polygons") != 45_140
                or topology.get("nonManifoldEdgesOverTwoFaces") != 0
                or topology.get("looseEdges") != 0
                or len(dimensions) != 3 or not 35.0 <= dimensions[2] <= 45.0):
            raise RuntimeError("v181 isolated skin topology contract is invalid")
        isolation = manifest.get("isolation", {})
        if (isolation.get("method")
                != "material-role-plus-largest-edge-connected-surface"
                or isolation.get("retainedConnectedComponentFaces") != 45_140):
            raise RuntimeError("v181 connected-component isolation contract is invalid")
        required = "gahyeon-keentools-skin-target-v181.fbx"
        if required not in files:
            raise RuntimeError("v181 package lacks the isolated skin FBX payload")
        source = PACKAGE_DIR / required
        entry = files[required]
        if (not source.is_file() or source.stat().st_size != entry["bytes"]
                or sha256_v183(source) != entry["sha256"]):
            raise RuntimeError("v181 FBX lineage mismatch")
        self.source = source
        self.source_sha256 = entry["sha256"]
        return manifest

    def _import_source(self):
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", str(self.source))
        task.set_editor_property("destination_path", f"{ASSET_ROOT}/Input")
        task.set_editor_property("destination_name", "SM_Gahyeon_KeenTools_v183")
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
            raise RuntimeError("KeenTools target is not a StaticMesh")
        return mesh

    def _build_scene(self):
        self.mesh = self._import_source()
        if not unreal.EditorLevelLibrary.new_level(TARGET_MAP):
            raise RuntimeError("failed to create v183 conform map")
        self.world = unreal.EditorLevelLibrary.get_editor_world()
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        self.preview = actors.spawn_actor_from_class(
            unreal.StaticMeshActor,
            unreal.Vector(0.0, 0.0, self.target_offset_z_cm),
            # Unreal Python's positional order is roll, pitch, yaw.
            unreal.Rotator(0.0, 0.0, 180.0 if self.rotate_target_yaw_180 else 0.0),
        )
        self.preview.set_actor_label("KeenToolsTarget_v183")
        self.preview.static_mesh_component.set_editor_property("static_mesh", self.mesh)
        neutral = unreal.EditorAssetLibrary.load_asset("/Engine/EngineMaterials/DefaultMaterial")
        if neutral is None:
            raise RuntimeError("default neutral material unavailable")
        for index in range(len(self.mesh.static_materials)):
            self.preview.static_mesh_component.set_material(index, neutral)
        self.origin, self.extent = self.preview.get_actor_bounds(False, True)
        if min(self.extent.x, self.extent.y, self.extent.z) <= 0.1:
            raise RuntimeError(f"implausible imported KeenTools bounds: {self.extent}")
        for label, yaw in (("North", 0.0), ("East", 90.0),
                           ("South", 180.0), ("West", -90.0)):
            light = actors.spawn_actor_from_class(
                unreal.DirectionalLight, self.origin, unreal.Rotator(-28.0, yaw, 0.0))
            light.set_actor_label(f"{label}_KeenTools_v183")
            component = light.get_component_by_class(unreal.DirectionalLightComponent)
            component.set_editor_property("intensity", 1.8)
            component.set_editor_property("cast_shadows", False)
        sky = actors.spawn_actor_from_class(unreal.SkyLight, self.origin, unreal.Rotator())
        sky.light_component.set_editor_property("intensity", 1.0)

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
            camera.set_actor_label(f"KeenTools_{name}_v183")
            camera.camera_component.set_editor_property("field_of_view", FOV_DEGREES)
            location = self.origin + offset
            camera.set_actor_location(location, False, False)
            camera.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(location, self.origin), False)
            self.cameras.append((name, camera))
        if not unreal.EditorLoadingAndSavingUtils.save_map(self.world, TARGET_MAP):
            raise RuntimeError("failed to save v183 conform map")

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
            raise RuntimeError("UE face tracker found no valid frontal KeenTools portrait")
        return scored

    def _finish(self):
        self._shutdown()
        subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
        scored = self._track_portraits(subsystem)
        count, name, camera, portrait, image_size, tracked = scored[0]
        head_vertices, head_indices, *_ = subsystem.get_mesh_data_for_conforming(self.mesh)
        if self.rotate_target_yaw_180:
            head_vertices = [
                unreal.Vector3f(-vertex.x, -vertex.y, vertex.z)
                for vertex in head_vertices
            ]
        if len(head_vertices) < 1_000 or len(head_indices) < 3_000:
            raise RuntimeError("KeenTools target topology extraction is implausibly small")
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
            raise RuntimeError("failed to create or lock v183 MetaHuman Character")
        conformed = False
        try:
            params = unreal.ConformTargetParams()
            params.conform_target_mesh.target_parts_type = unreal.TargetPartsType.HEAD_ONLY
            params.conform_target_mesh.head_vertices = head_vertices
            params.conform_target_mesh.head_vertex_indices = head_indices
            params.auto_solve = True
            # UE 5.8's interactive import tool assigns this exact identifier
            # for TargetPartsType.HEAD_ONLY. The raw API does not supply the
            # default and the autorigger otherwise fails to find a pipeline.
            params.body_conform_solve_settings.pipeline_name = "head_only"
            use_face_curves = os.environ.get("GAHYEON_DISABLE_FACE_CURVES") != "1"
            params.curve_tracking_points = tracked if use_face_curves else {}
            use_preset_keypoints = os.environ.get("GAHYEON_USE_PRESET_KEYPOINTS") == "1"
            preset_keypoint_records = []
            if use_preset_keypoints:
                if not self.rotate_target_yaw_180:
                    raise RuntimeError("preset keypoint mapping requires the validated 180-degree target orientation")
                transient = {}
                for skeletal_mesh in unreal.ObjectIterator(unreal.SkeletalMesh):
                    object_path = skeletal_mesh.get_path_name()
                    if "MetaHumanCharacterEditorSubsystem" not in object_path:
                        continue
                    if skeletal_mesh.get_name().startswith("FaceMesh"):
                        transient["face"] = skeletal_mesh
                    elif skeletal_mesh.get_name().startswith("BodyMesh"):
                        transient["body"] = skeletal_mesh
                if set(transient) != {"face", "body"}:
                    raise RuntimeError(f"missing transient MetaHuman template meshes: {transient}")
                extraction = subsystem.get_mesh_for_body_conforming_from_template(
                    character,
                    transient["body"],
                    transient["face"],
                    match_vertices_by_u_vs=False,
                )
                if not isinstance(extraction, tuple) or len(extraction) != 2:
                    raise RuntimeError(f"unexpected MetaHuman template extraction result: {extraction}")
                _status, template_vertices = extraction
                presets = subsystem.get_preset_body_key_points(character)
                facial_presets = []
                for preset_name, vertex_index in presets.items():
                    label = str(preset_name)
                    if not label.startswith("P") or not label[1:].isdigit():
                        continue
                    ordinal = int(label[1:])
                    if 1 <= ordinal <= 61 and 0 <= vertex_index < len(template_vertices):
                        vertex = template_vertices[vertex_index]
                        facial_presets.append((
                            ordinal,
                            label,
                            vertex_index,
                            (vertex.x, vertex.y, vertex.z),
                        ))
                if len(facial_presets) != 61:
                    raise RuntimeError(f"expected 61 facial preset keypoints, got {len(facial_presets)}")
                source_mins = [min(record[3][axis] for record in facial_presets) for axis in range(3)]
                source_maxs = [max(record[3][axis] for record in facial_presets) for axis in range(3)]
                target_tuples = [(vertex.x, vertex.y, vertex.z) for vertex in head_vertices]
                target_mins = [min(vertex[axis] for vertex in target_tuples) for axis in range(3)]
                target_maxs = [max(vertex[axis] for vertex in target_tuples) for axis in range(3)]
                keypoint_targets = {}
                for ordinal, label, vertex_index, source_position in facial_presets:
                    estimate = []
                    for axis in range(3):
                        source_span = source_maxs[axis] - source_mins[axis]
                        if source_span <= 0.001:
                            raise RuntimeError(f"degenerate preset source span on axis {axis}")
                        fraction = (source_position[axis] - source_mins[axis]) / source_span
                        estimate.append(target_mins[axis] + fraction * (target_maxs[axis] - target_mins[axis]))
                    nearest = min(
                        target_tuples,
                        key=lambda vertex: sum((vertex[axis] - estimate[axis]) ** 2 for axis in range(3)),
                    )
                    distance = math.sqrt(sum((nearest[axis] - estimate[axis]) ** 2 for axis in range(3)))
                    target_position = unreal.Vector3f(nearest[0], nearest[1], nearest[2])
                    keypoint_targets[vertex_index] = target_position
                    preset_keypoint_records.append({
                        "name": label,
                        "ordinal": ordinal,
                        "metaHumanVertexIndex": vertex_index,
                        "targetPosition": [target_position.x, target_position.y, target_position.z],
                        "affineProjectionDistanceCm": distance,
                    })
                params.key_point_targets = keypoint_targets
            view = unreal.MinimalViewInfo()
            # Match the interactive UE 5.8 mesh-import tool: MeshOffset moves
            # only the preview component. Solver vertices remain mesh-local,
            # and the captured camera is translated back into that local frame.
            camera_location = camera.get_actor_location()
            view.location = unreal.Vector(
                camera_location.x,
                camera_location.y,
                camera_location.z - self.target_offset_z_cm,
            )
            view.rotation = camera.get_actor_rotation()
            view.fov = FOV_DEGREES
            view.aspect_ratio = float(image_size.x) / float(image_size.y)
            view.projection_mode = unreal.CameraProjectionMode.PERSPECTIVE
            params.camera_view_info = view
            params.image_size = image_size
            key = unreal.MetaHumanCharacterTargetMeshKey()
            key.head_mesh = self.mesh
            align_first = os.environ.get("GAHYEON_ALIGN_HEAD_FIRST") == "1"
            if align_first and not subsystem.align_to_target_meshes(character, key, params):
                raise RuntimeError("UE 5.8 align_to_target_meshes failed")
            if not subsystem.conform_to_target_meshes(character, key, params):
                raise RuntimeError("UE 5.8 conform_to_target_meshes failed")
            skip_a_pose_commit = os.environ.get("GAHYEON_SKIP_APOSE_COMMIT") == "1"
            if not skip_a_pose_commit:
                subsystem.commit_posed_state_as_a_pose(character, key)
            if not unreal.EditorAssetLibrary.save_asset(TARGET_CHARACTER, only_if_is_dirty=True):
                raise RuntimeError("failed to save v183 conformed MetaHuman")
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
                 "sha256": sha256_v183(item[3])}
                for item in scored
            ],
            "selectedPortrait": {"axis": name, "trackedCurveCount": count,
                                 "path": str(portrait), "sameCameraUsedForConform": True},
            "faceCurveConstraintsApplied": use_face_curves,
            "presetKeypointConstraintsApplied": use_preset_keypoints,
            "presetKeypointConstraintCount": len(preset_keypoint_records),
            "presetKeypointConstraints": preset_keypoint_records,
            "targetTopology": {"vertices": len(head_vertices),
                               "triangles": len(head_indices) // 3},
            "targetOffsetCm": [0.0, 0.0, self.target_offset_z_cm],
            "targetYawRotationDegrees": 180.0 if self.rotate_target_yaw_180 else 0.0,
            "alignHeadApplied": align_first,
            "aPoseCommitApplied": not skip_a_pose_commit,
            "diagnosticOnly": skip_a_pose_commit,
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


def start_adaptive_custom_head_conform_v183():
    global _driver_v183
    _driver_v183 = AdaptiveCustomHeadConformDriverV183()


start_adaptive_custom_head_conform_v183()
