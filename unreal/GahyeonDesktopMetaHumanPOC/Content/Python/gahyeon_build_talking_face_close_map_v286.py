"""Clone the talking QA map and seal its real full-body camera at 85 mm."""

import json

import unreal


SOURCE_MAP = "/Game/Gahyeon/TalkingPOC/v275/QA/L_Gahyeon_TalkingPIE_v275"
TARGET_MAP = "/Game/Gahyeon/TalkingPOC/v286/QA/L_Gahyeon_TalkingFaceClose_v286"
SEQUENCE = "/Game/Gahyeon/TalkingPOC/v270/Sequence/LS_GahyeonTalkingControlRig_v270"
CAMERA_LABEL = "FullBodyCamera_v255"
FOCAL_LENGTH_MM = 85.0


if unreal.EditorAssetLibrary.does_asset_exist(TARGET_MAP):
    raise RuntimeError(f"refusing to overwrite immutable map: {TARGET_MAP}")
if not unreal.EditorAssetLibrary.does_asset_exist(SOURCE_MAP):
    raise RuntimeError(f"source talking map unavailable: {SOURCE_MAP}")
if not unreal.EditorAssetLibrary.does_asset_exist(SEQUENCE):
    raise RuntimeError(f"talking sequence unavailable: {SEQUENCE}")

target_world = unreal.EditorAssetLibrary.duplicate_asset(SOURCE_MAP, TARGET_MAP)
if target_world is None:
    raise RuntimeError(f"failed to duplicate talking map to: {TARGET_MAP}")
cameras = unreal.GameplayStatics.get_all_actors_of_class(
    target_world, unreal.CineCameraActor
)
camera = next(
    (actor for actor in cameras if actor.get_actor_label() == CAMERA_LABEL),
    None,
)
if camera is None:
    raise RuntimeError(
        "sealed QA camera unavailable in duplicated world; found: "
        + ", ".join(sorted(actor.get_actor_label() for actor in cameras))
    )

component = camera.get_cine_camera_component()
previous_focal_length = float(component.current_focal_length)
component.set_editor_property("current_focal_length", FOCAL_LENGTH_MM)
component.set_editor_property("aspect_ratio", 1.0)
if not unreal.EditorAssetLibrary.save_loaded_asset(
    target_world, only_if_is_dirty=False
):
    raise RuntimeError(f"failed to save close-up talking map: {TARGET_MAP}")

report = {
    "schemaVersion": 1,
    "iteration": "v286",
    "status": "draft-face-close-map-ready",
    "sourceMap": SOURCE_MAP,
    "map": TARGET_MAP,
    "sequence": SEQUENCE,
    "camera": camera.get_actor_label(),
    "previousFocalLengthMm": previous_focal_length,
    "focalLengthMm": FOCAL_LENGTH_MM,
    "aspectRatio": 1.0,
    "identityChanged": False,
    "visualValidationPending": True,
    "humanApproved": False,
    "productionReady": False,
    "automaticApproval": False,
}
unreal.log("GAHYEON_V286_FACE_CLOSE_MAP_READY=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
