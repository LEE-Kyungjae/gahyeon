"""Create a full-body-camera variant without changing the verified v094 sequence."""

import json
import os
from pathlib import Path

import unreal


SOURCE = "/Game/Gahyeon/TalkingPOC/v094/Sequence/LS_GahyeonTalkingControlRig_v094"
DESTINATION = "/Game/Gahyeon/TalkingPOC/v096/Sequence"
NAME = "LS_GahyeonTalkingFullBody_v096"
FOCAL_LENGTH_MM = 18.0


def build_talking_full_body_v096():
    output_asset = f"{DESTINATION}/{NAME}"
    if unreal.EditorAssetLibrary.does_asset_exist(output_asset):
        raise RuntimeError(f"refusing to overwrite v096 sequence: {output_asset}")
    source = unreal.load_asset(SOURCE)
    if source is None:
        raise RuntimeError(f"source sequence unavailable: {SOURCE}")
    sequence = unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(
        NAME, DESTINATION, source
    )
    if sequence is None:
        raise RuntimeError("failed to duplicate v094 sequence")

    camera_components = []
    templates = []
    for spawnable in sequence.get_spawnables():
        template = spawnable.get_object_template()
        templates.append(f"{spawnable.get_name()}:{template.get_class().get_name()}")
        components = []
        if isinstance(template, unreal.CineCameraComponent):
            components = [template]
        elif isinstance(template, unreal.Actor):
            components = list(template.get_components_by_class(unreal.CineCameraComponent))
        for camera in components:
            camera.set_editor_property("current_focal_length", FOCAL_LENGTH_MM)
            focus = camera.get_editor_property("focus_settings")
            focus.set_editor_property("focus_method", unreal.CameraFocusMethod.DISABLE)
            camera.set_editor_property("focus_settings", focus)
            camera_components.append(camera.get_name())
    if len(camera_components) != 1:
        raise RuntimeError(
            f"expected exactly one CineCameraComponent, got {camera_components}; "
            f"spawnables={templates}"
        )
    if not unreal.EditorAssetLibrary.save_loaded_asset(sequence, only_if_is_dirty=False):
        raise RuntimeError("failed to save v096 full-body sequence")

    receipt = {
        "schemaVersion": 1,
        "iteration": "v096",
        "state": "full-body-camera-sequence-built",
        "sourceSequence": SOURCE,
        "levelSequence": output_asset,
        "cameraComponent": camera_components[0],
        "focalLengthMm": FOCAL_LENGTH_MM,
        "runtimePlaybackVerified": False,
        "humanApproved": False,
        "productionReady": False,
        "automaticApproval": False,
    }
    receipt_path = Path(os.environ["GAHYEON_V096_BUILD_RECEIPT"])
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon talking full-body sequence built: {output_asset}")


build_talking_full_body_v096()
