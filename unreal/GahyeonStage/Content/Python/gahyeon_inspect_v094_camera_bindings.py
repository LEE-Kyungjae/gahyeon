"""Read-only inspection of the exported v094 sequence camera bindings."""

import unreal


SEQUENCE = "/Game/Gahyeon/TalkingPOC/v094/Sequence/LS_GahyeonTalkingControlRig_v094"


def inspect_v094_camera_bindings():
    sequence = unreal.load_asset(SEQUENCE)
    if sequence is None:
        raise RuntimeError(f"sequence unavailable: {SEQUENCE}")
    for binding in sequence.get_bindings():
        unreal.log(f"V094_BINDING name={binding.get_name()}")
        for track in binding.get_tracks():
            unreal.log(
                f"V094_TRACK binding={binding.get_name()} "
                f"class={track.get_class().get_name()} display={track.get_display_name()}"
            )
            for section in track.get_sections():
                channels = section.get_all_channels()
                unreal.log(
                    f"V094_SECTION class={section.get_class().get_name()} "
                    f"channels={[channel.get_name() for channel in channels]}"
                )
                for channel in channels:
                    default = channel.get_default() if channel.has_default() else None
                    unreal.log(
                        f"V094_CHANNEL track={track.get_display_name()} "
                        f"name={channel.get_name()} default={default} "
                        f"keys={[key.get_value() for key in channel.get_keys()]}"
                    )


inspect_v094_camera_bindings()
