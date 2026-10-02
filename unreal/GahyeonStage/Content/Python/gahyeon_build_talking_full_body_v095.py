"""Create an immutable full-body-camera variant of the verified v094 talking sequence."""

import json
import os
from pathlib import Path

import unreal


SOURCE = "/Game/Gahyeon/TalkingPOC/v094/Sequence/LS_GahyeonTalkingControlRig_v094"
DESTINATION = "/Game/Gahyeon/TalkingPOC/v095/Sequence"
NAME = "LS_GahyeonTalkingFullBody_v095"
FOCAL_LENGTH_MM = 20.0


def build_talking_full_body_v095():
    output_asset = f"{DESTINATION}/{NAME}"
    if unreal.EditorAssetLibrary.does_asset_exist(output_asset):
        raise RuntimeError(f"refusing to overwrite v095 sequence: {output_asset}")
    source = unreal.load_asset(SOURCE)
    if source is None:
        raise RuntimeError(f"source sequence unavailable: {SOURCE}")
    sequence = unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(
        NAME, DESTINATION, source
    )
    if sequence is None:
        raise RuntimeError("failed to duplicate v094 sequence")

    cameras = []
    for spawnable in sequence.get_spawnables():
        template = spawnable.get_object_template()
        if isinstance(template, unreal.CineCameraActor):
            camera = template.get_cine_camera_component()
            camera.set_editor_property("current_focal_length", FOCAL_LENGTH_MM)
            focus = camera.get_editor_property("focus_settings")
            focus.set_editor_property("focus_method", unreal.CameraFocusMethod.DISABLE)
            camera.set_editor_property("focus_settings", focus)
            cameras.append(spawnable.get_name())
    if len(cameras) != 1:
        raise RuntimeError(f"expected exactly one sequence camera, got {cameras}")
    if not unreal.EditorAssetLibrary.save_loaded_asset(sequence, only_if_is_dirty=False):
        raise RuntimeError("failed to save v095 full-body sequence")

    receipt = {
        "schemaVersion": 1,
        "iteration": "v095",
        "state": "full-body-camera-sequence-built",
        "sourceSequence": SOURCE,
        "levelSequence": output_asset,
        "cameraSpawnable": cameras[0],
        "focalLengthMm": FOCAL_LENGTH_MM,
        "runtimePlaybackVerified": False,
        "humanApproved": False,
        "productionReady": False,
        "automaticApproval": False,
    }
    receipt_path = Path(os.environ["GAHYEON_V095_BUILD_RECEIPT"])
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon talking full-body sequence built: {output_asset}")


build_talking_full_body_v095()
