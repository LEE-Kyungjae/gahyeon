"""Build fixed-camera layered-Dynamics sequences for every retained desktop action."""

import json
import math
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
REGISTRY = ROOT / "character_pipeline/config/living-character-runtime-v604.json"
OUTPUT = ROOT / "artifacts/living-character-poc-v641-desktop-action-sequences/report.json"
ROOT_PATH = "/Game/LivingCharacterPOC/v641"
CONTROL_RIGS = {
    "stella-lily": "/Game/LivingCharacterPOC/v633/ControlRig/CR_Stella_HairClothingDynamics_v633",
    "ururu": "/Game/LivingCharacterPOC/v636/ControlRig/CR_Ururu_HairClothingDynamics_v636",
}
DISPLAY_NAMES = {"stella-lily": "StellaLily", "ururu": "Ururu"}


def add_v641_rect_light(actors, label, location, target, intensity):
    light = actors.spawn_actor_from_class(
        unreal.RectLight,
        location,
        unreal.MathLibrary.find_look_at_rotation(location, target),
    )
    light.set_actor_label(label)
    component = light.get_component_by_class(unreal.RectLightComponent)
    component.set_editor_property("intensity", intensity)
    component.set_editor_property("source_width", 120.0)
    component.set_editor_property("source_height", 140.0)


def build_v641_character_map(character_id, mesh):
    display = DISPLAY_NAMES[character_id]
    map_path = f"{ROOT_PATH}/QA/L_{display}DesktopActions_v641"
    if unreal.EditorAssetLibrary.does_asset_exist(map_path):
        raise RuntimeError(f"refusing to overwrite immutable map: {map_path}")
    if not unreal.EditorLevelLibrary.new_level(map_path):
        raise RuntimeError(f"failed to create map: {map_path}")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    character = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector())
    character.set_actor_label(f"{display}_DesktopActions_v641")
    character.get_component_by_class(unreal.SkeletalMeshComponent).set_editor_property(
        "skeletal_mesh_asset", mesh
    )
    origin, extent = character.get_actor_bounds(False, True)
    target = unreal.Vector(origin.x, origin.y, origin.z + extent.z * 0.18)
    camera_location = target + unreal.Vector(0.0, 430.0, 8.0)
    camera = actors.spawn_actor_from_class(
        unreal.CineCameraActor,
        camera_location,
        unreal.MathLibrary.find_look_at_rotation(camera_location, target),
    )
    camera.set_actor_label(f"CAM_{display}DesktopActions_v641")
    camera.camera_component.set_editor_property("current_focal_length", 50.0)
    camera.camera_component.set_editor_property("current_aperture", 5.6)
    add_v641_rect_light(
        actors, f"KEY_{display}_v641", target + unreal.Vector(-130, 180, 90), target, 3800.0
    )
    add_v641_rect_light(
        actors, f"FILL_{display}_v641", target + unreal.Vector(130, 150, 35), target, 2100.0
    )
    add_v641_rect_light(
        actors, f"RIM_{display}_v641", target + unreal.Vector(0, -120, 90), target, 2500.0
    )
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
        raise RuntimeError(f"failed to save map: {map_path}")
    return map_path, character, camera


def build_v641_action_sequence(character_id, motion_id, animation_path, control_rig, character, camera):
    display = DISPLAY_NAMES[character_id]
    sequence_root = f"{ROOT_PATH}/Sequence/{display}"
    sequence_name = f"LS_{display}_{motion_id}_v641"
    sequence_path = f"{sequence_root}/{sequence_name}"
    if unreal.EditorAssetLibrary.does_asset_exist(sequence_path):
        raise RuntimeError(f"refusing to overwrite immutable sequence: {sequence_path}")
    animation = unreal.load_asset(animation_path)
    if not animation:
        raise RuntimeError(f"missing animation: {animation_path}")
    component = character.get_component_by_class(unreal.SkeletalMeshComponent)
    mesh = component.get_editor_property("skeletal_mesh_asset")
    if animation.get_editor_property("skeleton") != mesh.get_editor_property("skeleton"):
        raise RuntimeError(f"animation skeleton mismatch: {character_id}/{motion_id}")
    duration = float(animation.get_play_length())
    end_frame = max(2, int(math.ceil(duration * 30.0)) + 1)
    sequence = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        sequence_name,
        sequence_root,
        unreal.LevelSequence,
        unreal.LevelSequenceFactoryNew(),
    )
    if not sequence:
        raise RuntimeError(f"failed to create sequence: {sequence_path}")
    sequence.set_display_rate(unreal.FrameRate(30, 1))
    sequence.set_tick_resolution(unreal.FrameRate(24000, 1))
    sequence.set_playback_start(1)
    sequence.set_playback_end(end_frame)
    unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(sequence)
    sequencer = unreal.get_editor_subsystem(unreal.LevelSequenceEditorSubsystem)
    bindings = sequencer.add_actors([character, camera])
    by_name = {str(binding.get_name()): binding for binding in bindings}
    character_binding = by_name[character.get_actor_label()]
    camera_binding = by_name[camera.get_actor_label()]
    animation_section = character_binding.add_track(
        unreal.MovieSceneSkeletalAnimationTrack
    ).add_section()
    animation_section.set_range(1, end_frame)
    animation_section.params.animation = animation
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    rig_track = unreal.ControlRigSequencerLibrary.find_or_create_control_rig_track(
        world,
        sequence,
        control_rig.get_control_rig_class(),
        character_binding,
        is_layered_control_rig=True,
    )
    if not rig_track:
        raise RuntimeError(f"failed to layer dynamics: {character_id}/{motion_id}")
    unreal.ControlRigSequencerLibrary.set_control_rig_priority_order(rig_track, 200)
    cut = sequence.add_track(unreal.MovieSceneCameraCutTrack).add_section()
    cut.set_range(1, end_frame)
    binding_id = unreal.MovieSceneObjectBindingID()
    binding_id.set_editor_property("guid", camera_binding.get_id())
    cut.set_camera_binding_id(binding_id)
    unreal.LevelSequenceEditorBlueprintLibrary.refresh_current_level_sequence()
    if not unreal.EditorAssetLibrary.save_loaded_asset(sequence, only_if_is_dirty=False):
        raise RuntimeError(f"failed to save sequence: {sequence_path}")
    proxies = unreal.ControlRigSequencerLibrary.get_control_rigs(sequence)
    if len(proxies) != 1 or not unreal.ControlRigSequencerLibrary.is_layered_control_rig(
        proxies[0].control_rig
    ):
        raise RuntimeError(f"layered dynamics validation failed: {sequence_path}")
    return {
        "motion": motion_id,
        "animation": animation_path,
        "sequence": sequence_path,
        "durationSeconds": duration,
        "playbackRange": [1, end_frame],
        "layeredDynamics": True,
    }


def build_desktop_action_sequences_v641():
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to overwrite immutable report: {OUTPUT}")
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    records = {}
    for character_id in ("stella-lily", "ururu"):
        character = registry["characters"][character_id]
        mesh = unreal.load_asset(character["skeletalMesh"])
        control_rig = unreal.load_asset(CONTROL_RIGS[character_id])
        if not mesh or not control_rig:
            raise RuntimeError(f"missing character dependency: {character_id}")
        map_path, actor, camera = build_v641_character_map(character_id, mesh)
        actions = [
            build_v641_action_sequence(
                character_id,
                motion_id,
                animation_path,
                control_rig,
                actor,
                camera,
            )
            for motion_id, animation_path in character["motions"].items()
        ]
        records[character_id] = {
            "map": map_path,
            "mesh": character["skeletalMesh"],
            "controlRig": CONTROL_RIGS[character_id],
            "actions": actions,
        }
    report = {
        "schemaVersion": 1,
        "iteration": "v641",
        "status": "draft-desktop-action-sequences-ready",
        "registry": str(REGISTRY.relative_to(ROOT)),
        "characters": records,
        "hypothesis": "Every retained motion can share a fixed character QA map and add the validated native secondary-motion Control Rig after its body animation.",
        "visualValidationPending": True,
        "humanApproved": False,
        "releaseEligible": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.SystemLibrary.quit_editor()


build_desktop_action_sequences_v641()
