"""Build a full-body v094 talking variant by changing its focal-length track."""

import json
import os
from pathlib import Path

import unreal


SOURCE = "/Game/Gahyeon/TalkingPOC/v094/Sequence/LS_GahyeonTalkingControlRig_v094"
DESTINATION = "/Game/Gahyeon/TalkingPOC/v097/Sequence"
NAME = "LS_GahyeonTalkingFullBody_v097"
FOCAL_LENGTH_MM = 18.0


def build_talking_full_body_v097():
    output_asset = f"{DESTINATION}/{NAME}"
    if unreal.EditorAssetLibrary.does_asset_exist(output_asset):
        raise RuntimeError(f"refusing to overwrite v097 sequence: {output_asset}")
    source = unreal.load_asset(SOURCE)
    if source is None:
        raise RuntimeError(f"source sequence unavailable: {SOURCE}")
    sequence = unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(
        NAME, DESTINATION, source
    )
    if sequence is None:
        raise RuntimeError("failed to duplicate v094 sequence")

    focal_channels = []
    for binding in sequence.get_bindings():
        if binding.get_name() != "CameraComponent":
            continue
        for track in binding.get_tracks():
            if str(track.get_display_name()) != "CurrentFocalLength":
                continue
            for section in track.get_sections():
                for channel in section.get_all_channels():
                    channel.set_default(FOCAL_LENGTH_MM)
                    for key in channel.get_keys():
                        key.set_value(FOCAL_LENGTH_MM)
                    focal_channels.append(channel.get_name())
    if len(focal_channels) != 1:
        raise RuntimeError(f"expected one focal-length channel, got {focal_channels}")
    if not unreal.EditorAssetLibrary.save_loaded_asset(sequence, only_if_is_dirty=False):
        raise RuntimeError("failed to save v097 full-body sequence")

    receipt = {
        "schemaVersion": 1,
        "iteration": "v097",
        "state": "full-body-camera-sequence-built",
        "sourceSequence": SOURCE,
        "levelSequence": output_asset,
        "focalLengthChannel": focal_channels[0],
        "focalLengthMm": FOCAL_LENGTH_MM,
        "runtimePlaybackVerified": False,
        "humanApproved": False,
        "productionReady": False,
        "automaticApproval": False,
    }
    receipt_path = Path(os.environ["GAHYEON_V097_BUILD_RECEIPT"])
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon talking full-body sequence built: {output_asset}")


build_talking_full_body_v097()
