"""Build head-to-toe framing by dollying the camera behind its 5mm lens."""
import unreal

SOURCE = "/Game/Gahyeon/TalkingPOC/v094/Sequence/LS_GahyeonTalkingControlRig_v094"
DESTINATION = "/Game/Gahyeon/TalkingPOC/v102/Sequence"
NAME = "LS_GahyeonTalkingFullBody_v102"


def build_talking_full_body_v102():
    output = f"{DESTINATION}/{NAME}"
    if unreal.EditorAssetLibrary.does_asset_exist(output):
        raise RuntimeError(f"refusing to overwrite v102 sequence: {output}")
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
                        name = channel.get_name()
                        if str(track.get_display_name()) == "CurrentFocalLength":
                            channel.set_default(5.0)
                            changed.append("focal")
                        elif name.startswith("Location.X"):
                            channel.set_default(-45.0)
                            changed.append("dolly")
                        elif name.startswith("Location.Z"):
                            channel.set_default(125.0)
                            changed.append("height")
    if sorted(changed) != ["dolly", "focal", "height"]:
        raise RuntimeError(f"camera contract mismatch: {changed}")
    if not unreal.EditorAssetLibrary.save_loaded_asset(sequence, only_if_is_dirty=False):
        raise RuntimeError("failed to save v102 sequence")
    unreal.log(f"Gahyeon v102 head-to-toe sequence built: {output}")


build_talking_full_body_v102()
