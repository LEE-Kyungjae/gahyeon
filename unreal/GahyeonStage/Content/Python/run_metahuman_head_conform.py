"""Reusable fail-closed UE 5.8 head conform driven by a JSON contract."""

import hashlib
import json
import os
from pathlib import Path
import traceback

import unreal


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_character_conform_config():
    config_path = Path(os.environ.get("CHARACTER_CONFORM_CONFIG", ""))
    if not config_path.is_file():
        raise RuntimeError("CHARACTER_CONFORM_CONFIG must name a JSON file")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schemaVersion") != 1 or config.get("engineVersion") != "5.8":
        raise RuntimeError("unsupported character conform contract")
    claims = config.get("claims", {})
    if any(claims.get(name) is not False for name in (
        "identityApproved", "automaticApproval", "productionReady"
    )):
        raise RuntimeError("pre-conform claims must remain false")
    if config.get("faceConstraintMode", "tracked-orthographic") not in (
        "tracked-orthographic", "none"
    ):
        raise RuntimeError("unsupported faceConstraintMode")
    return config_path, config


def run_metahuman_head_conform():
    config_path, config = load_character_conform_config()
    output = Path(config["outputDirectory"])
    character_path = config["targetCharacter"]
    if output.exists():
        raise RuntimeError(f"refusing to overwrite immutable output: {output}")
    if unreal.EditorAssetLibrary.does_asset_exist(character_path):
        raise RuntimeError(f"refusing to overwrite immutable asset: {character_path}")
    output.mkdir(parents=True, exist_ok=False)
    character = None
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    try:
        face_mode = config.get("faceConstraintMode", "tracked-orthographic")
        portrait = None
        image_size = None
        tracked = {}
        if face_mode == "tracked-orthographic":
            portrait = Path(config["portrait"])
            if not portrait.is_file() or sha256_file(portrait) != config["portraitSha256"]:
                raise RuntimeError("portrait lineage mismatch")
            image_size, pixels = unreal.PromotedFrameUtils.get_promoted_frame_as_pixel_array_from_disk(
                str(portrait)
            )
            expected_size = config["camera"]["imageSize"]
            if [image_size.x, image_size.y] != expected_size:
                raise RuntimeError(f"portrait size mismatch: {image_size}")
            tracked = subsystem.track_face_landmarks_from_image(
                pixels, image_size.x, image_size.y
            )
            if isinstance(tracked, tuple) and len(tracked) == 1:
                tracked = tracked[0]
            if not tracked or not hasattr(tracked, "items") or len(tracked) < 10:
                raise RuntimeError("face tracker did not produce a valid contour set")

        mesh = unreal.load_asset(config["targetMesh"])
        if mesh is None:
            raise RuntimeError(f"target mesh missing: {config['targetMesh']}")
        vertices, indices, *_ = subsystem.get_mesh_data_for_conforming(mesh)
        if len(vertices) < 1_000 or len(indices) < 3_000:
            raise RuntimeError("target topology is implausibly small")
        yaw = float(config.get("targetYawRotationDegrees", 0.0))
        if yaw == 180.0:
            vertices = [unreal.Vector3f(-v.x, -v.y, v.z) for v in vertices]
        elif yaw != 0.0:
            raise RuntimeError("only validated target yaw values 0 and 180 are supported")

        package, asset_name = character_path.rsplit("/", 1)
        character = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            asset_name=asset_name,
            package_path=package,
            asset_class=unreal.MetaHumanCharacter,
            factory=unreal.new_object(type=unreal.MetaHumanCharacterFactoryNew),
        )
        if character is None or not subsystem.try_add_object_to_edit(character):
            raise RuntimeError("failed to create or lock MetaHuman Character")

        params = unreal.ConformTargetParams()
        params.conform_target_mesh.target_parts_type = unreal.TargetPartsType.HEAD_ONLY
        params.conform_target_mesh.head_vertices = vertices
        params.conform_target_mesh.head_vertex_indices = indices
        params.auto_solve = True
        params.body_conform_solve_settings.pipeline_name = "head_only"
        params.curve_tracking_points = tracked

        camera = config.get("camera")
        if face_mode == "tracked-orthographic":
            if camera.get("projection") != "orthographic":
                raise RuntimeError("tracked mode accepts sealed orthographic cameras only")
            view = unreal.MinimalViewInfo()
            view.location = unreal.Vector(*camera["locationCm"])
            rotation = camera["rotationDegrees"]
            view.rotation = unreal.Rotator(
                pitch=float(rotation[0]), yaw=float(rotation[1]), roll=float(rotation[2])
            )
            view.projection_mode = unreal.CameraProjectionMode.ORTHOGRAPHIC
            view.ortho_width = float(camera["orthoWidthCm"])
            view.aspect_ratio = float(image_size.x) / float(image_size.y)
            params.camera_view_info = view
            params.image_size = image_size

        key = unreal.MetaHumanCharacterTargetMeshKey()
        key.head_mesh = mesh
        if not subsystem.align_to_target_meshes(character, key, params):
            raise RuntimeError("align_to_target_meshes failed")
        if not subsystem.conform_to_target_meshes(character, key, params):
            raise RuntimeError("conform_to_target_meshes failed")
        if not unreal.EditorAssetLibrary.save_asset(character_path, only_if_is_dirty=True):
            raise RuntimeError("failed to save conformed MetaHuman Character")

        curve_points = sum(
            len(value.get_editor_property("tracking_points")) for value in tracked.values()
        )
        receipt = {
            "schemaVersion": 1,
            "characterId": config["characterId"],
            "iteration": config["iteration"],
            "state": "metahuman-conformed-awaiting-five-view-human-review",
            "config": {"path": str(config_path), "sha256": sha256_file(config_path)},
            "faceConstraintMode": face_mode,
            "portrait": ({"path": str(portrait), "sha256": config["portraitSha256"]}
                         if portrait is not None else None),
            "targetMesh": config["targetMesh"],
            "targetCharacter": character_path,
            "targetTopology": {"vertices": len(vertices), "triangles": len(indices) // 3},
            "trackedCurveCount": len(tracked),
            "trackedPointCount": curve_points,
            "camera": camera,
            "targetYawRotationDegrees": yaw,
            "identityApproved": False,
            "automaticApproval": False,
            "productionReady": False
        }
        (output / "conform-receipt.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        unreal.log(f"Reusable MetaHuman head conform complete: {character_path}")
    except Exception as error:
        if character is not None and subsystem.is_object_added_for_editing(character):
            subsystem.remove_object_to_edit(character)
        if unreal.EditorAssetLibrary.does_asset_exist(character_path):
            unreal.EditorAssetLibrary.delete_asset(character_path)
        (output / "failure-receipt.json").write_text(json.dumps({
            "schemaVersion": 1,
            "characterId": config.get("characterId"),
            "iteration": config.get("iteration"),
            "state": "failed-closed",
            "errorType": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
            "identityApproved": False,
            "productionReady": False
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        raise
    finally:
        if character is not None and subsystem.is_object_added_for_editing(character):
            subsystem.remove_object_to_edit(character)
        unreal.SystemLibrary.quit_editor()


run_metahuman_head_conform()
