"""Build the final wider head-to-toe talking camera variant."""
import unreal

SOURCE = "/Game/Gahyeon/TalkingPOC/v094/Sequence/LS_GahyeonTalkingControlRig_v094"
DESTINATION = "/Game/Gahyeon/TalkingPOC/v101/Sequence"
NAME = "LS_GahyeonTalkingFullBody_v101"


def build_talking_full_body_v101():
    output = f"{DESTINATION}/{NAME}"
    if unreal.EditorAssetLibrary.does_asset_exist(output):
        raise RuntimeError(f"refusing to overwrite v101 sequence: {output}")
    sequence = unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(
        NAME, DESTINATION, unreal.load_asset(SOURCE)
    )
    if sequence is None:
        raise RuntimeError("failed to duplicate v094 sequence")
    changed = []
    for binding in sequence.get_bindings():
        if binding.get_name() == "CameraComponent":
            for track in binding.get_tracks():
                for section in track.get_sections():
                    for channel in section.get_all_channels():
                        if str(track.get_display_name()) == "CurrentFocalLength":
                            channel.set_default(3.2)
                            changed.append("focal")
                        elif channel.get_name().startswith("Location.Z"):
                            channel.set_default(125.0)
                            changed.append("height")
    if sorted(changed) != ["focal", "height"]:
        raise RuntimeError(f"camera contract mismatch: {changed}")
    if not unreal.EditorAssetLibrary.save_loaded_asset(sequence, only_if_is_dirty=False):
        raise RuntimeError("failed to save v101 sequence")
    unreal.log(f"Gahyeon v101 head-to-toe sequence built: {output}")


build_talking_full_body_v101()
