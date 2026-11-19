"""Conform Ururu using its validated neutral reference and sealed v660 head mesh."""

import hashlib
import json
import math
from pathlib import Path

import unreal


ROOT = Path("/Users/ze/work/gahyeonbot")
SOURCE = ROOT / "artifacts/living-character-poc-v659-unreal-axis-heads/ururu-neutral-head-v659.fbx"
SOURCE_SHA256 = "28910ddc9790d1600022097f25b45682910f50f427274d2d612a847efd605210"
REFERENCE = ROOT / "artifacts/living-character-poc-v546-ururu-textured-evidence/face-front.png"
OUTPUT = ROOT / "artifacts/living-character-poc-v669-ururu-reference-metahuman-conform"
TARGET_MESH = "/Game/LivingCharacterPOC/v660/Input/SM_Ururu_UEAxisHead_v660"
TARGET_CHARACTER = "/Game/LivingCharacterPOC/v669/Character/MHC_Ururu_Draft_v669"
FOV_DEGREES = 36.0


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def conform_ururu_reference_metahuman_v669():
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to overwrite immutable v669 output: {OUTPUT}")
    if not SOURCE.is_file() or _sha256(SOURCE) != SOURCE_SHA256:
        raise RuntimeError("sealed Ururu v659 source lineage differs")
    if not REFERENCE.is_file():
        raise RuntimeError(f"validated Ururu reference is missing: {REFERENCE}")
    if unreal.EditorAssetLibrary.does_asset_exist(TARGET_CHARACTER):
        raise RuntimeError(f"refusing to overwrite immutable asset: {TARGET_CHARACTER}")
    mesh = unreal.load_asset(TARGET_MESH)
    if mesh is None or mesh.get_class().get_name() != "StaticMesh":
        raise RuntimeError("sealed Ururu v660 head is not a StaticMesh")
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    image_size, pixels = unreal.PromotedFrameUtils.get_promoted_frame_as_pixel_array_from_disk(
        str(REFERENCE)
    )
    tracked = subsystem.track_face_landmarks_from_image(pixels, image_size.x, image_size.y)
    if isinstance(tracked, tuple) and len(tracked) == 1:
        tracked = tracked[0]
    if not tracked or not hasattr(tracked, "items"):
        raise RuntimeError("UE face tracker found no curves on validated Ururu reference")
    head_vertices, head_indices, *_ = subsystem.get_mesh_data_for_conforming(mesh)
    if len(head_vertices) < 1000 or len(head_indices) < 3000:
        raise RuntimeError("Ururu target topology extraction is implausibly small")

    bounds = mesh.get_bounds()
    origin = bounds.origin
    extent = bounds.box_extent
    distance = max(extent.x, extent.z) * 1.42 / math.tan(math.radians(FOV_DEGREES * 0.5))
    camera_location = origin + unreal.Vector(0.0, distance, 0.0)
    camera_rotation = unreal.MathLibrary.find_look_at_rotation(camera_location, origin)
    package, name = TARGET_CHARACTER.rsplit("/", 1)
    character = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        asset_name=name,
        package_path=package,
        asset_class=unreal.MetaHumanCharacter,
        factory=unreal.new_object(type=unreal.MetaHumanCharacterFactoryNew),
    )
    if character is None:
        raise RuntimeError("failed to create Ururu v669 MetaHuman Character")
    if not subsystem.try_add_object_to_edit(character):
        unreal.EditorAssetLibrary.delete_asset(TARGET_CHARACTER)
        raise RuntimeError("failed to lock Ururu v669 MetaHuman Character for editing")
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
        view.location = camera_location
        view.rotation = camera_rotation
        view.fov = FOV_DEGREES
        view.aspect_ratio = float(image_size.x) / float(image_size.y)
        view.projection_mode = unreal.CameraProjectionMode.PERSPECTIVE
        params.camera_view_info = view
        params.image_size = image_size
        key = unreal.MetaHumanCharacterTargetMeshKey()
        key.head_mesh = mesh
        if not subsystem.conform_to_target_meshes(character, key, params):
            raise RuntimeError("UE 5.8 Ururu v669 conform_to_target_meshes failed")
        subsystem.commit_posed_state_as_a_pose(character, key)
        if not unreal.EditorAssetLibrary.save_asset(TARGET_CHARACTER, only_if_is_dirty=True):
            raise RuntimeError("failed to save Ururu v669 MetaHuman draft")
        conformed = True
    finally:
        if subsystem.is_object_added_for_editing(character):
            subsystem.remove_object_to_edit(character)
        if not conformed:
            unreal.EditorAssetLibrary.delete_asset(TARGET_CHARACTER)
    OUTPUT.mkdir(parents=True, exist_ok=False)
    receipt = {
        "schemaVersion": 1,
        "iteration": "v669",
        "state": "draft-conformed-awaiting-fixed-camera-surface-qa",
        "engine": "5.8",
        "characterId": "ururu",
        "source": {"path": str(SOURCE), "sha256": SOURCE_SHA256},
        "reference": {"path": str(REFERENCE), "sha256": _sha256(REFERENCE)},
        "targetMesh": TARGET_MESH,
        "targetCharacter": TARGET_CHARACTER,
        "referenceTrackingOnly": True,
        "camera": {
            "locationCm": [camera_location.x, camera_location.y, camera_location.z],
            "rotationDegrees": [camera_rotation.pitch, camera_rotation.yaw, camera_rotation.roll],
            "fovDegrees": FOV_DEGREES,
            "projectionAssumption": "perspective approximation of validated orthographic reference",
        },
        "targetTopology": {
            "vertices": len(head_vertices),
            "triangles": len(head_indices) // 3,
        },
        "trackedCurveCount": len(tracked),
        "hypothesis": (
            "A readable validated Ururu reference provides stable face landmarks while "
            "the sealed v660 mesh remains the authoritative 3D conform target."
        ),
        "decision": "retain as draft until fixed-camera surface QA",
        "automaticApproval": False,
        "identityApproved": False,
        "productionReady": False,
    }
    (OUTPUT / "conform-receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    unreal.SystemLibrary.quit_editor()


conform_ururu_reference_metahuman_v669()
