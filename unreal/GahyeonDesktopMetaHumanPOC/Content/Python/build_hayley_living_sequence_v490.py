"""Build a single-character UE sequence that exercises verified living-character states."""

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
MAP = "/Game/LivingCharacterPOC/v490/QA/L_HayleyLivingSequence_v490"
SEQUENCE_ROOT = "/Game/LivingCharacterPOC/v490/Sequence"
SEQUENCE_NAME = "LS_HayleyLivingSequence_v490"
SEQUENCE = f"{SEQUENCE_ROOT}/{SEQUENCE_NAME}"
MESH = "/Game/LivingCharacterPOC/v448/Characters/HayleyBindClean/Hayley_BindPoseClean_v447"
REPORT = ROOT / "artifacts/living-character-poc-v490-hayley-living-sequence/report.json"
STATES = (
    ("listening", "/Game/LivingCharacterPOC/v484/Animation/subtle/AS_HayleyClean_ButWait_subtle_v484", 2.5),
    ("thinking", "/Game/LivingCharacterPOC/v466/Animation/AS_HayleyClean_CyberIdle_v466", 4.0),
    ("speaking", "/Game/LivingCharacterPOC/v472/Animation/AS_HayleyClean_Narration_v472", 6.0),
    ("presenting", "/Game/LivingCharacterPOC/v484/Animation/present/AS_HayleyClean_ButWait_present_v484", 2.5),
    ("emphasizing", "/Game/LivingCharacterPOC/v484/Animation/emphasis/AS_HayleyClean_ButWait_emphasis_v484", 2.5),
    ("posture", "/Game/LivingCharacterPOC/v452/Animation/AS_HayleyClean_StandSit_v452", 3.8),
)


def add_rect_light(actors, location, target, intensity):
    light = actors.spawn_actor_from_class(
        unreal.RectLight, location, unreal.MathLibrary.find_look_at_rotation(location, target)
    )
    component = light.get_component_by_class(unreal.RectLightComponent)
    component.set_editor_property("intensity", intensity)
    component.set_editor_property("source_width", 120.0)
    component.set_editor_property("source_height", 140.0)


def build_hayley_living_sequence_v490():
    if REPORT.exists() or unreal.EditorAssetLibrary.does_asset_exist(MAP) or unreal.EditorAssetLibrary.does_asset_exist(SEQUENCE):
        raise RuntimeError("refusing to overwrite immutable v490 outputs")
    mesh = unreal.load_asset(MESH)
    animations = [(state, path, seconds, unreal.load_asset(path)) for state, path, seconds in STATES]
    if mesh is None or any(animation is None for _, _, _, animation in animations):
        raise RuntimeError("one or more living-sequence dependencies are unavailable")
    skeleton = mesh.get_editor_property("skeleton")
    if any(animation.get_editor_property("skeleton") != skeleton for _, _, _, animation in animations):
        raise RuntimeError("living-sequence animation skeleton mismatch")
    if not unreal.EditorLevelLibrary.new_level(MAP):
        raise RuntimeError("failed to create v490 map")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    character = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0, 0, 0))
    character.set_actor_label("Hayley_LivingCharacter_v490")
    character.get_component_by_class(unreal.SkeletalMeshComponent).set_editor_property("skeletal_mesh_asset", mesh)
    origin, extent = character.get_actor_bounds(False, True)
    target = unreal.Vector(origin.x, origin.y, origin.z + extent.z * 0.15)
    camera_location = target + unreal.Vector(0, 440, 10)
    camera = actors.spawn_actor_from_class(
        unreal.CineCameraActor, camera_location, unreal.MathLibrary.find_look_at_rotation(camera_location, target)
    )
    camera.set_actor_label("CAM_HayleyLiving_v490")
    camera.set_editor_property("auto_activate_for_player", unreal.AutoReceiveInput.PLAYER0)
    camera.camera_component.set_editor_property("current_focal_length", 50.0)
    camera.camera_component.set_editor_property("current_aperture", 5.6)
    add_rect_light(actors, target + unreal.Vector(-130, 180, 90), target, 3800.0)
    add_rect_light(actors, target + unreal.Vector(130, 150, 35), target, 2100.0)
    add_rect_light(actors, target + unreal.Vector(0, -120, 90), target, 2500.0)
    sky = actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector())
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("intensity", 0.8)
    post = actors.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector())
    post.set_editor_property("unbound", True)
    settings = post.get_editor_property("settings")
    settings.set_editor_property("override_auto_exposure_method", True)
    settings.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)
    settings.set_editor_property("override_auto_exposure_bias", True)
    settings.set_editor_property("auto_exposure_bias", 1.0)
    settings.set_editor_property("override_motion_blur_amount", True)
    settings.set_editor_property("motion_blur_amount", 0.0)
    post.set_editor_property("settings", settings)
    if not unreal.EditorLevelLibrary.save_current_level():
        raise RuntimeError("failed to save v490 map")
    sequence = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        SEQUENCE_NAME, SEQUENCE_ROOT, unreal.LevelSequence, unreal.LevelSequenceFactoryNew()
    )
    if sequence is None:
        raise RuntimeError("failed to create v490 Level Sequence")
    sequence.set_display_rate(unreal.FrameRate(30, 1))
    sequence.set_tick_resolution(unreal.FrameRate(24000, 1))
    unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(sequence)
    bindings = unreal.get_editor_subsystem(unreal.LevelSequenceEditorSubsystem).add_actors([character, camera])
    by_name = {str(binding.get_name()): binding for binding in bindings}
    character_binding = by_name["Hayley_LivingCharacter_v490"]
    camera_binding = by_name["CAM_HayleyLiving_v490"]
    track = character_binding.add_track(unreal.MovieSceneSkeletalAnimationTrack)
    cursor = 1
    timeline = []
    for state, path, seconds, animation in animations:
        duration = max(1, round(seconds * 30.0))
        section = track.add_section()
        section.set_range(cursor, cursor + duration)
        section.params.animation = animation
        timeline.append({"state": state, "animation": path, "startFrame": cursor, "endFrame": cursor + duration})
        cursor += duration
    sequence.set_playback_start(1)
    sequence.set_playback_end(cursor)
    cut = sequence.add_track(unreal.MovieSceneCameraCutTrack).add_section()
    cut.set_range(1, cursor)
    binding_id = unreal.MovieSceneObjectBindingID()
    binding_id.set_editor_property("guid", camera_binding.get_id())
    cut.set_camera_binding_id(binding_id)
    unreal.LevelSequenceEditorBlueprintLibrary.refresh_current_level_sequence()
    if not unreal.EditorAssetLibrary.save_loaded_asset(sequence, only_if_is_dirty=False):
        raise RuntimeError("failed to save v490 sequence")
    report = {
        "schemaVersion": 1, "iteration": "v490", "status": "draft-living-character-sequence-ready",
        "map": MAP, "sequence": SEQUENCE, "mesh": MESH, "displayRate": 30,
        "playbackRange": [1, cursor], "timeline": timeline,
        "humanApproved": False, "releaseEligible": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("HAYLEY_LIVING_SEQUENCE=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


build_hayley_living_sequence_v490()
