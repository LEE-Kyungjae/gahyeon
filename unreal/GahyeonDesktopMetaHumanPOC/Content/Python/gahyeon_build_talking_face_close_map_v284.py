"""Clone the talking QA map and seal an 85 mm conversational face camera."""

import json

import unreal


SOURCE_MAP = "/Game/Gahyeon/TalkingPOC/v275/QA/L_Gahyeon_TalkingPIE_v275"
TARGET_MAP = "/Game/Gahyeon/TalkingPOC/v284/QA/L_Gahyeon_TalkingFaceClose_v284"
SEQUENCE = "/Game/Gahyeon/TalkingPOC/v270/Sequence/LS_GahyeonTalkingControlRig_v270"
CAMERA_LABEL_FRAGMENT = "GahyeonTalkingPerformance_v092 Camera"
FOCAL_LENGTH_MM = 85.0


if unreal.EditorAssetLibrary.does_asset_exist(TARGET_MAP):
    raise RuntimeError(f"refusing to overwrite immutable map: {TARGET_MAP}")
if not unreal.EditorAssetLibrary.does_asset_exist(SOURCE_MAP):
    raise RuntimeError(f"source talking map unavailable: {SOURCE_MAP}")
if not unreal.EditorAssetLibrary.does_asset_exist(SEQUENCE):
    raise RuntimeError(f"talking sequence unavailable: {SEQUENCE}")
if not unreal.EditorAssetLibrary.duplicate_asset(SOURCE_MAP, TARGET_MAP):
    raise RuntimeError(f"failed to duplicate talking map to: {TARGET_MAP}")
if unreal.EditorLoadingAndSavingUtils.load_map(TARGET_MAP) is None:
    raise RuntimeError(f"failed to load duplicated map: {TARGET_MAP}")

actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
cameras = [
    actor
    for actor in actor_subsystem.get_all_level_actors()
    if isinstance(actor, unreal.CineCameraActor)
]
camera = next(
    (actor for actor in cameras if CAMERA_LABEL_FRAGMENT in actor.get_actor_label()),
    None,
)
if camera is None:
    raise RuntimeError(
        "talking performance camera unavailable; found: "
        + ", ".join(sorted(actor.get_actor_label() for actor in cameras))
    )

component = camera.get_cine_camera_component()
previous_focal_length = float(component.current_focal_length)
component.set_editor_property("current_focal_length", FOCAL_LENGTH_MM)
component.set_editor_property("aspect_ratio", 1.0)
if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level():
    raise RuntimeError(f"failed to save close-up talking map: {TARGET_MAP}")

report = {
    "schemaVersion": 1,
    "iteration": "v284",
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
unreal.log("GAHYEON_V284_FACE_CLOSE_MAP_READY=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
