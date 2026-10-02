"""Duplicate the talking sequence and seal a conservative full-face focal length."""

import json

import unreal


SOURCE_SEQUENCE = "/Game/Gahyeon/TalkingPOC/v270/Sequence/LS_GahyeonTalkingControlRig_v270"
TARGET_SEQUENCE = "/Game/Gahyeon/TalkingPOC/v291/Sequence/LS_GahyeonTalkingFaceClose_v291"
MAP = "/Game/Gahyeon/TalkingPOC/v275/QA/L_Gahyeon_TalkingPIE_v275"
CAMERA_COMPONENT_BINDING = "CameraComponent"
FOCAL_LENGTH_MM = 25.0


if unreal.EditorAssetLibrary.does_asset_exist(TARGET_SEQUENCE):
    raise RuntimeError(f"refusing to overwrite immutable sequence: {TARGET_SEQUENCE}")
sequence = unreal.EditorAssetLibrary.duplicate_asset(SOURCE_SEQUENCE, TARGET_SEQUENCE)
if sequence is None:
    raise RuntimeError(f"failed to duplicate sequence: {SOURCE_SEQUENCE}")

binding = next(
    (
        candidate
        for candidate in sequence.get_bindings()
        if str(candidate.get_name()) == CAMERA_COMPONENT_BINDING
    ),
    None,
)
if binding is None:
    raise RuntimeError(
        "camera component binding unavailable; found: "
        + ", ".join(sorted(str(item.get_name()) for item in sequence.get_bindings()))
    )

focal_tracks = [
    track
    for track in binding.get_tracks()
    if isinstance(track, unreal.MovieSceneFloatTrack)
    and (
        str(track.get_property_name()) == "CurrentFocalLength"
        or str(track.get_property_path()) == "CurrentFocalLength"
    )
]
focal_track = focal_tracks[0] if focal_tracks else binding.add_track(
    unreal.MovieSceneFloatTrack
)
if not focal_tracks:
    focal_track.set_property_name_and_path(
        "CurrentFocalLength", "CurrentFocalLength"
    )

sections = list(focal_track.get_sections())
focal_section = sections[0] if sections else focal_track.add_section()
focal_section.set_range(sequence.get_playback_start(), sequence.get_playback_end())
channels = list(unreal.MovieSceneSectionExtensions.get_all_channels(focal_section))
if len(channels) != 1:
    raise RuntimeError(f"expected one focal-length channel, got {len(channels)}")
channel = channels[0]
for key in list(channel.get_keys()):
    channel.remove_key(key)
channel.add_key(unreal.FrameNumber(sequence.get_playback_start()), FOCAL_LENGTH_MM)
channel.add_key(unreal.FrameNumber(sequence.get_playback_end() - 1), FOCAL_LENGTH_MM)

if not unreal.EditorAssetLibrary.save_loaded_asset(sequence, only_if_is_dirty=False):
    raise RuntimeError(f"failed to save close-up sequence: {TARGET_SEQUENCE}")

report = {
    "schemaVersion": 1,
    "iteration": "v291",
    "status": "draft-full-face-sequence-ready",
    "sourceSequence": SOURCE_SEQUENCE,
    "sequence": TARGET_SEQUENCE,
    "map": MAP,
    "cameraComponentBinding": CAMERA_COMPONENT_BINDING,
    "focalLengthMm": FOCAL_LENGTH_MM,
    "hypothesis": (
        "A conservative 25 mm override will enlarge the v287 bust framing enough "
        "for full-face blink and gaze QA without repeating v290's 85 mm crop."
    ),
    "identityChanged": False,
    "visualValidationPending": True,
    "humanApproved": False,
    "productionReady": False,
    "automaticApproval": False,
}
unreal.log("GAHYEON_V291_FACE_CLOSE_SEQUENCE_READY=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
