"""Build the measured head-to-toe talking camera variant."""

import unreal

SOURCE = "/Game/Gahyeon/TalkingPOC/v094/Sequence/LS_GahyeonTalkingControlRig_v094"
DESTINATION = "/Game/Gahyeon/TalkingPOC/v100/Sequence"
NAME = "LS_GahyeonTalkingFullBody_v100"
FOCAL_LENGTH_MM = 3.5
CAMERA_HEIGHT_CM = 125.0


def build_talking_full_body_v100():
    output = f"{DESTINATION}/{NAME}"
    if unreal.EditorAssetLibrary.does_asset_exist(output):
        raise RuntimeError(f"refusing to overwrite v100 sequence: {output}")
    source = unreal.load_asset(SOURCE)
    sequence = unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(
        NAME, DESTINATION, source
    )
    if source is None or sequence is None:
        raise RuntimeError("v094 source unavailable or duplication failed")
    changed = []
    for binding in sequence.get_bindings():
        if binding.get_name() == "CameraComponent":
            for track in binding.get_tracks():
                display = str(track.get_display_name())
                for section in track.get_sections():
                    for channel in section.get_all_channels():
                        if display == "CurrentFocalLength":
                            channel.set_default(FOCAL_LENGTH_MM)
                            changed.append("focal")
                        elif channel.get_name().startswith("Location.Z"):
                            channel.set_default(CAMERA_HEIGHT_CM)
                            changed.append("height")
    if sorted(changed) != ["focal", "height"]:
        raise RuntimeError(f"expected focal and height channels, got {changed}")
    if not unreal.EditorAssetLibrary.save_loaded_asset(sequence, only_if_is_dirty=False):
        raise RuntimeError("failed to save v100 sequence")
    unreal.log(f"Gahyeon v100 head-to-toe sequence built: {output}")


build_talking_full_body_v100()
