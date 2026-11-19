"""Build and open a non-destructive MetaHuman Identity solve candidate."""

import os
import unreal


ASSET_PATH = "/Game/Gahyeon/CharacterPipeline/v002/IdentityInput/SM_Gahyeon_IdentityInput_v002"
IDENTITY_PATH = "/Game/Gahyeon/CharacterPipeline/v002/Identity/MHI_Gahyeon_v002"
CAPTURE_PATH = "/Game/Gahyeon/CharacterPipeline/v002/Identity/SM_Gahyeon_IdentityInput_v002_CaptureData"
SOLVE_IDENTITY_PATH = "/Game/Gahyeon/CharacterPipeline/v024/Identity/MHI_Gahyeon_v024"
SOLVE_IDENTITY_DIRECTORY = "/Game/Gahyeon/CharacterPipeline/v024/Identity"
_callback = None
_solve_callback = None
_solve_wait_ticks = 0


def _track_and_conform(_delta_seconds):
    global _solve_callback, _solve_wait_ticks
    _solve_wait_ticks += 1
    if _solve_wait_ticks < 30:
        return
    handle = _solve_callback
    _solve_callback = None
    unreal.unregister_slate_post_tick_callback(handle)
    result = unreal.GahyeonMetaHumanQALibrary.track_and_conform_identity(SOLVE_IDENTITY_PATH)
    if isinstance(result, tuple):
        success = bool(result[0])
        message = str(result[1]) if len(result) > 1 else "bridge returned no diagnostic"
    else:
        success = bool(result)
        message = "bridge returned success" if success else "bridge rejected tracking or conform"
    unreal.log(f"Gahyeon QA conform result: success={success} message={message}")
    if not success:
        raise RuntimeError(message)
    solved = unreal.EditorAssetLibrary.load_asset(SOLVE_IDENTITY_PATH)
    if not unreal.EditorAssetLibrary.save_loaded_asset(solved, only_if_is_dirty=False):
        raise RuntimeError(f"failed to save conformed Identity: {SOLVE_IDENTITY_PATH}")
    if not unreal.EditorAssetLibrary.save_directory(
        SOLVE_IDENTITY_DIRECTORY,
        only_if_is_dirty=False,
        recursive=True,
    ):
        raise RuntimeError(f"failed to save conformed Identity dependencies: {SOLVE_IDENTITY_DIRECTORY}")


def _open_identity_input(_delta_seconds):
    global _callback, _solve_callback
    mesh_capture_data_class = getattr(unreal, "MeshCaptureData", None)
    if mesh_capture_data_class is None:
        handle = _callback
        _callback = None
        unreal.unregister_slate_post_tick_callback(handle)
        unreal.log_warning(
            "Legacy MeshCaptureData startup solve is unavailable in this UE 5.8 session; "
            "use a newly created MetaHuman Character and Conform From Custom Mesh/Identity."
        )
        return
    asset = unreal.EditorAssetLibrary.load_asset(ASSET_PATH)
    if asset is None:
        return
    handle = _callback
    _callback = None
    unreal.unregister_slate_post_tick_callback(handle)
    capture_data = unreal.EditorAssetLibrary.load_asset(CAPTURE_PATH)
    if capture_data is None:
        capture_data = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "SM_Gahyeon_IdentityInput_v002_CaptureData",
            "/Game/Gahyeon/CharacterPipeline/v002/Identity",
            mesh_capture_data_class,
            None,
        )
        if capture_data is None:
            raise RuntimeError(f"failed to create immutable mesh capture data: {CAPTURE_PATH}")
        capture_data.set_editor_property("target_mesh", asset)
        if not unreal.EditorAssetLibrary.save_loaded_asset(capture_data, only_if_is_dirty=False):
            raise RuntimeError(f"failed to save immutable mesh capture data: {CAPTURE_PATH}")
    solved = unreal.EditorAssetLibrary.load_asset(SOLVE_IDENTITY_PATH)
    if solved is None:
        solved = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "MHI_Gahyeon_v024",
            SOLVE_IDENTITY_DIRECTORY,
            unreal.MetaHumanIdentity,
            unreal.MetaHumanIdentityFactoryNew(),
        )
        if solved is None:
            raise RuntimeError(f"failed to create clean v024 solve candidate: {SOLVE_IDENTITY_PATH}")
        solve_face = solved.get_or_create_part_of_class(unreal.MetaHumanIdentityFace)
        solve_pose = unreal.new_object(type=unreal.MetaHumanIdentityPose, outer=solve_face)
        solve_face.add_pose_of_type(unreal.IdentityPoseType.NEUTRAL, solve_pose)
        solve_pose.set_capture_data(capture_data)
        solve_pose.fit_eyes = False
        solve_pose.load_default_tracker()
        if not unreal.EditorAssetLibrary.save_loaded_asset(solved, only_if_is_dirty=False):
            raise RuntimeError(f"failed to save clean v024 solve candidate: {SOLVE_IDENTITY_PATH}")
    unreal.EditorAssetLibrary.sync_browser_to_objects([SOLVE_IDENTITY_PATH])
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).open_editor_for_assets([solved])
    unreal.log(
        f"Gahyeon QA opened clean solve candidate: {SOLVE_IDENTITY_PATH} from {ASSET_PATH}"
    )
    _solve_callback = unreal.register_slate_post_tick_callback(_track_and_conform)


if os.environ.get("GAHYEON_IDENTITY_SOLVE_V059") == "1":
    from gahyeon_solve_head_only_identity_v059 import start_head_only_identity_v059

    start_head_only_identity_v059()
elif os.environ.get("GAHYEON_ENABLE_LEGACY_IDENTITY_STARTUP") == "1":
    _callback = unreal.register_slate_post_tick_callback(_open_identity_input)
