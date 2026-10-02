"""Create a deterministic Level Sequence for Diana's v041 primary-chain run QA."""

import json

import unreal


MAP = "/Game/Gahyeon/Character2/Diana/v041/QA/L_Diana_PrimaryChainRun_v041"
CHARACTER_LABEL = "Diana_v041_PrimaryChainRunDraft"
CAMERA_LABEL = "CAM_Diana_FullBody_v041"
ANIMATION_PATH = (
    "/Game/Gahyeon/Character2/Diana/v040/Animation/"
    "AS_Diana_RunForward_v244_PrimaryLegs_v040"
)
ROOT = "/Game/Gahyeon/Character2/Diana/v046/Sequence"
NAME = "LS_Diana_PrimaryChainRun_v046"
SEQUENCE_PATH = f"{ROOT}/{NAME}"
START_FRAME = 0
END_FRAME = 90


if unreal.EditorAssetLibrary.does_asset_exist(SEQUENCE_PATH):
    raise RuntimeError(f"refusing to overwrite immutable sequence: {SEQUENCE_PATH}")
if unreal.EditorLoadingAndSavingUtils.load_map(MAP) is None:
    raise RuntimeError(f"failed to load Diana v041 map: {MAP}")
animation = unreal.EditorAssetLibrary.load_asset(ANIMATION_PATH)
if animation is None:
    raise RuntimeError(f"animation unavailable: {ANIMATION_PATH}")

actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
character = next(
    (actor for actor in actors.get_all_level_actors()
     if actor.get_actor_label() == CHARACTER_LABEL),
    None,
)
camera = next(
    (actor for actor in actors.get_all_level_actors()
     if actor.get_actor_label() == CAMERA_LABEL),
    None,
)
if character is None or camera is None:
    raise RuntimeError("Diana v041 character or fixed camera unavailable")

sequence = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
    NAME, ROOT, unreal.LevelSequence, unreal.LevelSequenceFactoryNew()
)
if sequence is None:
    raise RuntimeError("failed to create Diana v046 Level Sequence")
sequence.set_display_rate(unreal.FrameRate(30, 1))
sequence.set_tick_resolution(unreal.FrameRate(24000, 1))
sequence.set_playback_start(START_FRAME)
sequence.set_playback_end(END_FRAME)
if not unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(sequence):
    raise RuntimeError("failed to open Diana v046 Level Sequence")

sequencer = unreal.get_editor_subsystem(unreal.LevelSequenceEditorSubsystem)
bindings = sequencer.add_actors([character, camera])
if len(bindings) != 2:
    raise RuntimeError(f"expected character and camera bindings, got {len(bindings)}")
binding_by_name = {str(binding.get_name()): binding for binding in bindings}
character_binding = binding_by_name.get(CHARACTER_LABEL)
camera_binding = binding_by_name.get(CAMERA_LABEL)
if character_binding is None or camera_binding is None:
    raise RuntimeError(f"unexpected binding names: {sorted(binding_by_name)}")

animation_track = character_binding.add_track(unreal.MovieSceneSkeletalAnimationTrack)
animation_section = animation_track.add_section()
animation_section.set_range(START_FRAME, END_FRAME)
animation_section.params.animation = animation

# UE 5.8 removed LevelSequence.add_master_track; the engine's bundled
# Sequencer/MRQ Python examples add the camera-cut track directly.
camera_cut_track = sequence.add_track(unreal.MovieSceneCameraCutTrack)
camera_cut_section = camera_cut_track.add_section()
camera_cut_section.set_range(START_FRAME, END_FRAME)
camera_binding_id = unreal.MovieSceneObjectBindingID()
camera_binding_id.set_editor_property("guid", camera_binding.get_id())
camera_cut_section.set_camera_binding_id(camera_binding_id)

unreal.LevelSequenceEditorBlueprintLibrary.refresh_current_level_sequence()
if not unreal.EditorAssetLibrary.save_loaded_asset(sequence, only_if_is_dirty=False):
    raise RuntimeError("failed to save Diana v046 Level Sequence")

report = {
    "schemaVersion": 1,
    "iteration": "v046",
    "status": "draft-mrq-sequence-ready",
    "map": MAP,
    "sequence": SEQUENCE_PATH,
    "animation": ANIMATION_PATH,
    "displayRate": 30,
    "playbackRange": [START_FRAME, END_FRAME],
    "bindings": sorted(binding_by_name),
    "cameraCutBinding": CAMERA_LABEL,
    "visualValidationPending": True,
    "automaticApproval": False,
}
unreal.log("DIANA_V046_SEQUENCE_READY=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
