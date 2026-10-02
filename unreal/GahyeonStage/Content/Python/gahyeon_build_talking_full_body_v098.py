"""Build a wider full-body talking sequence after visual rejection of v097."""

import unreal


SOURCE = "/Game/Gahyeon/TalkingPOC/v094/Sequence/LS_GahyeonTalkingControlRig_v094"
DESTINATION = "/Game/Gahyeon/TalkingPOC/v098/Sequence"
NAME = "LS_GahyeonTalkingFullBody_v098"
FOCAL_LENGTH_MM = 5.0


def build_talking_full_body_v098():
    output_asset = f"{DESTINATION}/{NAME}"
    if unreal.EditorAssetLibrary.does_asset_exist(output_asset):
        raise RuntimeError(f"refusing to overwrite v098 sequence: {output_asset}")
    source = unreal.load_asset(SOURCE)
    if source is None:
        raise RuntimeError(f"source sequence unavailable: {SOURCE}")
    sequence = unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(
        NAME, DESTINATION, source
    )
    if sequence is None:
        raise RuntimeError("failed to duplicate v094 sequence")
    changed = []
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
                    changed.append(channel.get_name())
    if len(changed) != 1:
        raise RuntimeError(f"expected one focal-length channel, got {changed}")
    if not unreal.EditorAssetLibrary.save_loaded_asset(sequence, only_if_is_dirty=False):
        raise RuntimeError("failed to save v098 full-body sequence")
    unreal.log(f"Gahyeon v098 full-body sequence built at {FOCAL_LENGTH_MM}mm: {output_asset}")


build_talking_full_body_v098()
