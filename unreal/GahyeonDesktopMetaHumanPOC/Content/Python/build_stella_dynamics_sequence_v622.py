"""Build a fixed-camera Stella living-idle sequence with layered Control Rig Dynamics."""

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
MAP = "/Game/LivingCharacterPOC/v622/QA/L_StellaDynamics_v622"
SEQUENCE_ROOT = "/Game/LivingCharacterPOC/v622/Sequence"
SEQUENCE_NAME = "LS_StellaDynamics_v622"
SEQUENCE = f"{SEQUENCE_ROOT}/{SEQUENCE_NAME}"
MESH = "/Game/LivingCharacterPOC/v572/Characters/StellaCentimeterNormalized/StellaLily_CentimeterNormalized_v571"
ANIMATION = "/Game/LivingCharacterPOC/v606/Animation/stella/AS_Stella_LivingIdle_v606"
CONTROL_RIG = "/Game/LivingCharacterPOC/v620/ControlRig/CR_Stella_HairDynamics_v620"
REPORT = ROOT / "artifacts/living-character-poc-v622-stella-dynamics-sequence/report.json"
END_FRAME = 305


def add_rect_light(actors, label, location, target, intensity):
    light = actors.spawn_actor_from_class(
        unreal.RectLight, location, unreal.MathLibrary.find_look_at_rotation(location, target)
    )
    light.set_actor_label(label)
    component = light.get_component_by_class(unreal.RectLightComponent)
    component.set_editor_property("intensity", intensity)
    component.set_editor_property("source_width", 120.0)
    component.set_editor_property("source_height", 140.0)


def build_stella_dynamics_sequence_v622():
    if REPORT.exists():
        raise RuntimeError(f"refusing to overwrite immutable output: {REPORT}")
    for path in (MAP, SEQUENCE):
        if unreal.EditorAssetLibrary.does_asset_exist(path):
            raise RuntimeError(f"refusing to overwrite immutable asset: {path}")

    mesh = unreal.load_asset(MESH)
    animation = unreal.load_asset(ANIMATION)
    control_rig = unreal.load_asset(CONTROL_RIG)
    if not mesh or not animation or not control_rig:
        raise RuntimeError("missing Stella dynamics sequence dependency")
    if animation.get_editor_property("skeleton") != mesh.get_editor_property("skeleton"):
        raise RuntimeError("Stella animation skeleton mismatch")

    if not unreal.EditorLevelLibrary.new_level(MAP):
        raise RuntimeError("failed to create v622 map")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    character = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector())
    character.set_actor_label("Stella_Dynamics_v622")
    component = character.get_component_by_class(unreal.SkeletalMeshComponent)
    component.set_editor_property("skeletal_mesh_asset", mesh)

    origin, extent = character.get_actor_bounds(False, True)
    target = unreal.Vector(origin.x, origin.y, origin.z + extent.z * 0.18)
    camera_location = target + unreal.Vector(0.0, 430.0, 8.0)
    camera = actors.spawn_actor_from_class(
        unreal.CineCameraActor,
        camera_location,
        unreal.MathLibrary.find_look_at_rotation(camera_location, target),
    )
    camera.set_actor_label("CAM_StellaDynamics_v622")
    camera.camera_component.set_editor_property("current_focal_length", 50.0)
    camera.camera_component.set_editor_property("current_aperture", 5.6)
    add_rect_light(actors, "KEY_v622", target + unreal.Vector(-130, 180, 90), target, 3800.0)
    add_rect_light(actors, "FILL_v622", target + unreal.Vector(130, 150, 35), target, 2100.0)
    add_rect_light(actors, "RIM_v622", target + unreal.Vector(0, -120, 90), target, 2500.0)
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
        raise RuntimeError("failed to save v622 map")

    sequence = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        SEQUENCE_NAME, SEQUENCE_ROOT, unreal.LevelSequence, unreal.LevelSequenceFactoryNew()
    )
    if not sequence:
        raise RuntimeError("failed to create v622 sequence")
    sequence.set_display_rate(unreal.FrameRate(30, 1))
    sequence.set_tick_resolution(unreal.FrameRate(24000, 1))
    sequence.set_playback_start(1)
    sequence.set_playback_end(END_FRAME)
    unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(sequence)
    sequencer = unreal.get_editor_subsystem(unreal.LevelSequenceEditorSubsystem)
    bindings = sequencer.add_actors([character, camera])
    by_name = {str(binding.get_name()): binding for binding in bindings}
    character_binding = by_name["Stella_Dynamics_v622"]
    camera_binding = by_name["CAM_StellaDynamics_v622"]

    anim_section = character_binding.add_track(unreal.MovieSceneSkeletalAnimationTrack).add_section()
    anim_section.set_range(1, END_FRAME)
    anim_section.params.animation = animation
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    rig_track = unreal.ControlRigSequencerLibrary.find_or_create_control_rig_track(
        world,
        sequence,
        control_rig.get_control_rig_class(),
        character_binding,
        is_layered_control_rig=True,
    )
    if not rig_track:
        raise RuntimeError("failed to create layered Control Rig track")
    unreal.ControlRigSequencerLibrary.set_control_rig_priority_order(rig_track, 200)

    cut = sequence.add_track(unreal.MovieSceneCameraCutTrack).add_section()
    cut.set_range(1, END_FRAME)
    binding_id = unreal.MovieSceneObjectBindingID()
    binding_id.set_editor_property("guid", camera_binding.get_id())
    cut.set_camera_binding_id(binding_id)
    unreal.LevelSequenceEditorBlueprintLibrary.refresh_current_level_sequence()
    if not unreal.EditorAssetLibrary.save_loaded_asset(sequence, only_if_is_dirty=False):
        raise RuntimeError("failed to save v622 sequence")

    proxies = unreal.ControlRigSequencerLibrary.get_control_rigs(sequence)
    report = {
        "schemaVersion": 1,
        "iteration": "v622",
        "status": "draft-layered-control-rig-sequence-ready",
        "map": MAP,
        "sequence": SEQUENCE,
        "mesh": MESH,
        "animation": ANIMATION,
        "controlRig": CONTROL_RIG,
        "playbackRange": [1, END_FRAME],
        "controlRigProxyCount": len(proxies),
        "layered": all(
            unreal.ControlRigSequencerLibrary.is_layered_control_rig(proxy.control_rig)
            for proxy in proxies
        ),
        "priorityOrder": unreal.ControlRigSequencerLibrary.get_control_rig_priority_order(rig_track),
        "hypothesis": "Layered Control Rig Dynamics modifies Stella hair after the retained v606 body animation.",
        "visualValidationPending": True,
        "humanApproved": False,
        "releaseEligible": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.SystemLibrary.quit_editor()


build_stella_dynamics_sequence_v622()
