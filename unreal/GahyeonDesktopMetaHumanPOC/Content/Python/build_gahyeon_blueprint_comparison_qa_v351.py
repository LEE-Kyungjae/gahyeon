"""Build persistent original versus v350 Gahyeon Blueprint visual QA."""

import json
from pathlib import Path

import unreal


ORIGINAL = (
    "/Game/Gahyeon/CharacterPipeline/v244/AssembledMedium/"
    "Gahyeon_AnimationPOC_v244/BP_Gahyeon_AnimationPOC_v244"
)
FIXED = "/Game/Gahyeon/CharacterPipeline/v350/BP_Gahyeon_HairShadowFixed_v350"
MAP = "/Game/Gahyeon/CharacterPipeline/v351/QA/L_GahyeonBlueprintCompare_v351"
SEQUENCE_ROOT = "/Game/Gahyeon/CharacterPipeline/v352/Sequence"
SEQUENCE_NAME = "LS_GahyeonBlueprintCompare_v352"
SEQUENCE = f"{SEQUENCE_ROOT}/{SEQUENCE_NAME}"
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v351-gahyeon-blueprint-comparison-build/report.json"
)
FACE_CENTER_Z = 152.23505401611328


def add_rect_light(actors, label, location, target, intensity):
    actor = actors.spawn_actor_from_class(
        unreal.RectLight,
        location,
        unreal.MathLibrary.find_look_at_rotation(location, target),
    )
    if actor is None:
        raise RuntimeError(f"failed to spawn {label}")
    actor.set_actor_label(label)
    component = actor.get_component_by_class(unreal.RectLightComponent)
    component.set_editor_property("intensity", intensity)
    component.set_editor_property("source_width", 100.0)
    component.set_editor_property("source_height", 110.0)


def hair_state(actor):
    hair = next(
        component for component in actor.get_components_by_class(unreal.GroomComponent)
        if str(component.get_name()) == "Hair"
    )
    return {
        "visible": bool(hair.is_visible()),
        "hiddenInGame": bool(hair.get_editor_property("hidden_in_game")),
        "castShadow": bool(hair.get_editor_property("cast_shadow")),
    }


def build_gahyeon_blueprint_comparison_qa_v351():
    for path in (MAP, SEQUENCE):
        if unreal.EditorAssetLibrary.does_asset_exist(path):
            raise RuntimeError(f"refusing to overwrite immutable asset: {path}")
    classes = {
        "Original": unreal.EditorAssetLibrary.load_blueprint_class(ORIGINAL),
        "Fixed": unreal.EditorAssetLibrary.load_blueprint_class(FIXED),
    }
    if any(value is None for value in classes.values()):
        raise RuntimeError(f"Blueprint class unavailable: {classes}")
    if not unreal.EditorLevelLibrary.new_level(MAP):
        raise RuntimeError("failed to create Blueprint comparison map")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    characters = []
    for name, x in (("Original", -42.0), ("Fixed", 42.0)):
        actor = actors.spawn_actor_from_class(classes[name], unreal.Vector(x, 0.0, 0.0))
        if actor is None:
            raise RuntimeError(f"failed to spawn {name} Gahyeon")
        actor.set_actor_label(f"Gahyeon_{name}_v351")
        characters.append((name, actor, hair_state(actor)))
    if characters[0][2]["castShadow"] is not True:
        raise RuntimeError(f"original Hair shadow unexpectedly disabled: {characters}")
    if characters[1][2]["castShadow"] is not False:
        raise RuntimeError(f"fixed Hair shadow unexpectedly enabled: {characters}")
    target = unreal.Vector(0.0, 0.0, FACE_CENTER_Z - 4.0)
    camera_location = target + unreal.Vector(0.0, 340.0, 0.0)
    camera = actors.spawn_actor_from_class(
        unreal.CineCameraActor,
        camera_location,
        unreal.MathLibrary.find_look_at_rotation(camera_location, target),
    )
    if camera is None:
        raise RuntimeError("failed to spawn Blueprint comparison camera")
    camera.set_actor_label("CAM_GahyeonBlueprintCompare_v351")
    camera.set_editor_property("auto_activate_for_player", unreal.AutoReceiveInput.PLAYER0)
    camera.camera_component.set_editor_property("current_focal_length", 85.0)
    camera.camera_component.set_editor_property("current_aperture", 8.0)
    add_rect_light(
        actors, "KEY_GahyeonBlueprintCompare_v351", target + unreal.Vector(-110, 170, 65), target, 4400.0
    )
    add_rect_light(
        actors, "FILL_GahyeonBlueprintCompare_v351", target + unreal.Vector(120, 150, 20), target, 2800.0
    )
    add_rect_light(
        actors, "RIM_GahyeonBlueprintCompare_v351", target + unreal.Vector(0, -110, 50), target, 3000.0
    )
    sky = actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector())
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("intensity", 0.8)
    post = actors.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector())
    post.set_editor_property("unbound", True)
    settings = post.get_editor_property("settings")
    settings.set_editor_property("override_auto_exposure_method", True)
    settings.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)
    settings.set_editor_property("override_auto_exposure_bias", True)
    settings.set_editor_property("auto_exposure_bias", 0.0)
    settings.set_editor_property("override_motion_blur_amount", True)
    settings.set_editor_property("motion_blur_amount", 0.0)
    post.set_editor_property("settings", settings)
    if not unreal.EditorLevelLibrary.save_current_level():
        raise RuntimeError("failed to save Blueprint comparison map")
    sequence = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        SEQUENCE_NAME, SEQUENCE_ROOT, unreal.LevelSequence, unreal.LevelSequenceFactoryNew()
    )
    if sequence is None:
        raise RuntimeError("failed to create Blueprint comparison sequence")
    sequence.set_display_rate(unreal.FrameRate(30, 1))
    sequence.set_tick_resolution(unreal.FrameRate(24000, 1))
    sequence.set_playback_start(0)
    sequence.set_playback_end(5)
    if not unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(sequence):
        raise RuntimeError("failed to open Blueprint comparison sequence")
    camera_binding = unreal.get_editor_subsystem(
        unreal.LevelSequenceEditorSubsystem
    ).add_actors([camera])[0]
    camera_cut = sequence.add_track(unreal.MovieSceneCameraCutTrack).add_section()
    camera_cut.set_range(0, 5)
    binding_id = unreal.MovieSceneObjectBindingID()
    binding_id.set_editor_property("guid", camera_binding.get_id())
    camera_cut.set_camera_binding_id(binding_id)
    if not unreal.EditorAssetLibrary.save_loaded_asset(sequence, only_if_is_dirty=False):
        raise RuntimeError("failed to save Blueprint comparison sequence")
    report = {
        "schemaVersion": 1,
        "iterations": ["v351", "v352"],
        "status": "draft-blueprint-comparison-ready",
        "map": MAP,
        "sequence": SEQUENCE,
        "characters": [
            {"name": name, "label": actor.get_actor_label(), "hair": state}
            for name, actor, state in characters
        ],
        "hypothesis": (
            "The reusable v350 Blueprint preserves Hair visibility and removes the "
            "excessive neck shadow by disabling only Hair cast_shadow."
        ),
        "visualValidationPending": True,
        "humanApproved": False,
        "productionReady": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("GAHYEON_V351_COMPARE=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


build_gahyeon_blueprint_comparison_qa_v351()
