"""Compare Diana reference pose with v345 idle under identical conditions."""

import json
from pathlib import Path

import unreal


MAP = "/Game/Gahyeon/Character2/Diana/v358/QA/L_DianaReferenceAnimationCompare_v358"
SEQUENCE_ROOT = "/Game/Gahyeon/Character2/Diana/v359/Sequence"
SEQUENCE_NAME = "LS_DianaReferenceAnimationCompare_v359"
SEQUENCE = f"{SEQUENCE_ROOT}/{SEQUENCE_NAME}"
MESH = "/Game/Gahyeon/Character2/Diana/v024/Source/SK_Diana_CM_v024"
ANIMATION = "/Game/Gahyeon/Character2/Diana/v345/Animation/AS_Diana_Idle_v244_APose_v345"
MATERIAL_ROOT = "/Game/Gahyeon/Character2/Diana/v002/Materials"
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v358-diana-reference-animation-comparison-build/report.json"
)


def require_asset_v358(path):
    asset = unreal.load_asset(path)
    if asset is None:
        raise RuntimeError(f"required asset unavailable: {path}")
    return asset


def add_rect_light_v358(actors, label, location, target, intensity):
    light = actors.spawn_actor_from_class(
        unreal.RectLight, location, unreal.MathLibrary.find_look_at_rotation(location, target)
    )
    light.set_actor_label(label)
    component = light.get_component_by_class(unreal.RectLightComponent)
    component.set_editor_property("intensity", intensity)
    component.set_editor_property("source_width", 100.0)
    component.set_editor_property("source_height", 120.0)


def build_diana_reference_animation_comparison_v358():
    for path in (MAP, SEQUENCE):
        if unreal.EditorAssetLibrary.does_asset_exist(path):
            raise RuntimeError(f"refusing to overwrite immutable asset: {path}")
    mesh = require_asset_v358(MESH)
    animation = require_asset_v358(ANIMATION)
    materials = [
        require_asset_v358(f"{MATERIAL_ROOT}/M_Diana_Slot{index:02d}_v002")
        for index in range(18)
    ]
    if not unreal.EditorLevelLibrary.new_level(MAP):
        raise RuntimeError("failed to create Diana comparison map")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    characters = []
    for label, x in (("Diana_Reference_v358", -42.0), ("Diana_Animated_v358", 42.0)):
        actor = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(x, 0.0, 0.0))
        actor.set_actor_label(label)
        component = actor.get_component_by_class(unreal.SkeletalMeshComponent)
        component.set_editor_property("skeletal_mesh_asset", mesh)
        for index, material in enumerate(materials):
            component.set_material(index, material)
        characters.append(actor)
    origin, extent = characters[0].get_actor_bounds(False, True)
    target = unreal.Vector(0.0, origin.y, origin.z)
    camera_location = target + unreal.Vector(0.0, 460.0, 5.0)
    camera = actors.spawn_actor_from_class(
        unreal.CineCameraActor,
        camera_location,
        unreal.MathLibrary.find_look_at_rotation(camera_location, target),
    )
    camera.set_actor_label("CAM_DianaReferenceAnimationCompare_v358")
    camera.set_editor_property("auto_activate_for_player", unreal.AutoReceiveInput.PLAYER0)
    camera.camera_component.set_editor_property("current_focal_length", 50.0)
    camera.camera_component.set_editor_property("current_aperture", 5.6)
    add_rect_light_v358(actors, "KEY_Diana_v358", target + unreal.Vector(-100, 160, 70), target, 4200.0)
    add_rect_light_v358(actors, "FILL_Diana_v358", target + unreal.Vector(110, 145, 30), target, 2300.0)
    add_rect_light_v358(actors, "RIM_Diana_v358", target + unreal.Vector(0, -100, 55), target, 2800.0)
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
        raise RuntimeError("failed to save Diana comparison map")
    sequence = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        SEQUENCE_NAME, SEQUENCE_ROOT, unreal.LevelSequence, unreal.LevelSequenceFactoryNew()
    )
    sequence.set_display_rate(unreal.FrameRate(30, 1))
    sequence.set_tick_resolution(unreal.FrameRate(24000, 1))
    sequence.set_playback_start(1)
    sequence.set_playback_end(31)
    unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(sequence)
    sequencer = unreal.get_editor_subsystem(unreal.LevelSequenceEditorSubsystem)
    bindings = sequencer.add_actors([characters[1], camera])
    by_name = {str(binding.get_name()): binding for binding in bindings}
    animated_binding = by_name["Diana_Animated_v358"]
    camera_binding = by_name["CAM_DianaReferenceAnimationCompare_v358"]
    section = animated_binding.add_track(unreal.MovieSceneSkeletalAnimationTrack).add_section()
    section.set_range(0, 31)
    section.params.animation = animation
    cut = sequence.add_track(unreal.MovieSceneCameraCutTrack).add_section()
    cut.set_range(1, 31)
    binding_id = unreal.MovieSceneObjectBindingID()
    binding_id.set_editor_property("guid", camera_binding.get_id())
    cut.set_camera_binding_id(binding_id)
    if not unreal.EditorAssetLibrary.save_loaded_asset(sequence, only_if_is_dirty=False):
        raise RuntimeError("failed to save Diana comparison sequence")
    report = {
        "schemaVersion": 1,
        "iterations": ["v358", "v359"],
        "status": "draft-reference-animation-comparison-ready",
        "map": MAP,
        "sequence": SEQUENCE,
        "mesh": MESH,
        "animation": ANIMATION,
        "referencePoseActor": "Diana_Reference_v358",
        "animatedActor": "Diana_Animated_v358",
        "hypothesis": (
            "If the reference actor is clean while the animated actor protrudes, the defect "
            "is introduced by retargeted auxiliary-bone transforms rather than source geometry."
        ),
        "visualValidationPending": True,
        "humanApproved": False,
        "productionReady": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("DIANA_V358_COMPARE=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


build_diana_reference_animation_comparison_v358()
