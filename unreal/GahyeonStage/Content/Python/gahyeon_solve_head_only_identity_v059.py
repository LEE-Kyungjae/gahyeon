"""Import and solve the immutable v059 head-only MetaHuman Identity input."""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import unreal


ITERATION = os.environ.get("GAHYEON_IDENTITY_SOLVE_VERSION", "v059")
if ITERATION not in {"v059", "v060", "v062", "v063", "v064", "v065", "v066", "v067", "v068", "v069", "v070", "v071"}:
    raise RuntimeError(f"unsupported head-only Identity iteration: {ITERATION}")
INPUT = Path(
    f"/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/metahuman-identity-head-only-{ITERATION}/"
    f"gahyeon-metahuman-head-only-{ITERATION}.obj"
)
INPUT_ASSET = f"/Game/Gahyeon/CharacterPipeline/{ITERATION}/IdentityInput/SM_Gahyeon_HeadOnly_{ITERATION}"
CAPTURE = f"/Game/Gahyeon/CharacterPipeline/{ITERATION}/Identity/SM_Gahyeon_HeadOnly_{ITERATION}_CaptureData"
IDENTITY = f"/Game/Gahyeon/CharacterPipeline/{ITERATION}/Identity/MHI_Gahyeon_HeadOnly_{ITERATION}"
IDENTITY_DIR = f"/Game/Gahyeon/CharacterPipeline/{ITERATION}/Identity"
_open_callback = None
_solve_callback = None
_ticks = 0


def _sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def _track_head_only_identity_v059(_delta_seconds):
    global _solve_callback, _ticks
    _ticks += 1
    wait_ticks = int(os.environ.get("GAHYEON_IDENTITY_SOLVE_WAIT_TICKS", "45"))
    if _ticks < wait_ticks:
        return
    handle = _solve_callback
    _solve_callback = None
    unreal.unregister_slate_post_tick_callback(handle)
    result = unreal.GahyeonMetaHumanQALibrary.track_and_conform_identity(IDENTITY)
    success = bool(result[0]) if isinstance(result, tuple) else bool(result)
    message = str(result[1]) if isinstance(result, tuple) and len(result) > 1 else str(result)
    if not success:
        raise RuntimeError(f"{ITERATION} head-only Identity solve failed: {message}")
    identity = unreal.EditorAssetLibrary.load_asset(IDENTITY)
    if identity is None or not unreal.EditorAssetLibrary.save_loaded_asset(identity, only_if_is_dirty=False):
        raise RuntimeError("failed to save v059 solved Identity")
    if not unreal.EditorAssetLibrary.save_directory(IDENTITY_DIR, only_if_is_dirty=False, recursive=True):
        raise RuntimeError("failed to save v059 solved Identity dependencies")
    workspace = Path(os.environ.get("GAHYEON_WORKSPACE", "/Users/ze/work/gahyeonbot"))
    receipt = workspace / f"artifacts/gahyeon-ch/metahuman-head-only-{ITERATION}-solve.json"
    if receipt.exists():
        raise RuntimeError(f"refusing to overwrite immutable solve receipt: {receipt}")
    assets = unreal.EditorAssetLibrary.list_assets(IDENTITY_DIR, recursive=True, include_folder=False)
    value = {
        "schemaVersion": 1,
        "observedAt": datetime.now(timezone.utc).isoformat(),
        "iteration": ITERATION,
        "input": {"path": str(INPUT), "sha256": _sha256(INPUT)},
        "inputAsset": INPUT_ASSET,
        "captureData": CAPTURE,
        "identityAsset": IDENTITY,
        "identityAssets": list(assets),
        "result": "SUCCESS",
        "diagnostic": message,
        "hypothesis": "A single head surface in UE Z-up coordinates prevents catastrophic marker tracking and conform collapse.",
        "status": "draft",
        "automaticApproval": False,
        "identityApproved": False,
        "productionReady": False,
        "aaaQualityClaim": False,
    }
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon {ITERATION} head-only Identity solve complete: {json.dumps(value)}")


def solve_head_only_identity_v059(_delta_seconds):
    global _open_callback, _solve_callback, _ticks
    if not INPUT.is_file():
        raise RuntimeError(f"v059 solve input missing: {INPUT}")
    receipt = Path(os.environ.get("GAHYEON_WORKSPACE", "/Users/ze/work/gahyeonbot")) / (
        f"artifacts/gahyeon-ch/metahuman-head-only-{ITERATION}-solve.json"
    )
    if receipt.exists():
        raise RuntimeError(f"refusing to overwrite immutable solve receipt: {receipt}")
    if any(unreal.EditorAssetLibrary.does_asset_exist(path) for path in (INPUT_ASSET, CAPTURE, IDENTITY)):
        raise RuntimeError("refusing to overwrite existing v059 Identity assets")
    handle = _open_callback
    _open_callback = None
    unreal.unregister_slate_post_tick_callback(handle)

    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(INPUT))
    task.set_editor_property("destination_path", INPUT_ASSET.rsplit("/", 1)[0])
    task.set_editor_property("destination_name", INPUT_ASSET.rsplit("/", 1)[1])
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", False)
    task.set_editor_property("save", True)
    options = unreal.FbxImportUI()
    options.set_editor_property("import_mesh", True)
    options.set_editor_property("import_as_skeletal", False)
    options.set_editor_property("import_materials", True)
    options.set_editor_property("import_textures", True)
    options.static_mesh_import_data.set_editor_property("combine_meshes", True)
    options.static_mesh_import_data.set_editor_property("convert_scene", False)
    options.static_mesh_import_data.set_editor_property("convert_scene_unit", False)
    task.set_editor_property("options", options)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh = unreal.EditorAssetLibrary.load_asset(INPUT_ASSET)
    if mesh is None or mesh.get_class().get_name() != "StaticMesh":
        raise RuntimeError("v059 head-only OBJ did not import as one StaticMesh")

    capture = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        CAPTURE.rsplit("/", 1)[1], CAPTURE.rsplit("/", 1)[0], unreal.MeshCaptureData, None
    )
    if capture is None:
        raise RuntimeError("failed to create v059 MeshCaptureData")
    capture.set_editor_property("target_mesh", mesh)
    if not unreal.EditorAssetLibrary.save_loaded_asset(capture, only_if_is_dirty=False):
        raise RuntimeError("failed to save v059 MeshCaptureData")
    identity = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        IDENTITY.rsplit("/", 1)[1], IDENTITY_DIR, unreal.MetaHumanIdentity,
        unreal.MetaHumanIdentityFactoryNew(),
    )
    if identity is None:
        raise RuntimeError("failed to create v059 MetaHuman Identity")
    face = identity.get_or_create_part_of_class(unreal.MetaHumanIdentityFace)
    pose = unreal.new_object(type=unreal.MetaHumanIdentityPose, outer=face)
    face.add_pose_of_type(unreal.IdentityPoseType.NEUTRAL, pose)
    pose.set_capture_data(capture)
    pose.fit_eyes = False
    pose.load_default_tracker()
    if not unreal.EditorAssetLibrary.save_loaded_asset(identity, only_if_is_dirty=False):
        raise RuntimeError("failed to save initial v059 MetaHuman Identity")
    _solve_callback = unreal.register_slate_post_tick_callback(_track_head_only_identity_v059)
    if os.environ.get("GAHYEON_IDENTITY_SOLVE_IMMEDIATE") == "1":
        _ticks = int(os.environ.get("GAHYEON_IDENTITY_SOLVE_WAIT_TICKS", "45"))
        _track_head_only_identity_v059(0.0)


def start_head_only_identity_v059():
    global _open_callback
    _open_callback = unreal.register_slate_post_tick_callback(solve_head_only_identity_v059)
