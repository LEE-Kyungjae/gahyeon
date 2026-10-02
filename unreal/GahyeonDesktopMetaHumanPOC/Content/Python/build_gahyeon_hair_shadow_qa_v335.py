"""Build a persistent Gahyeon hair-on versus hair-off neck shading comparison."""

import json
from pathlib import Path

import unreal


BLUEPRINT = (
    "/Game/Gahyeon/CharacterPipeline/v244/AssembledMedium/"
    "Gahyeon_AnimationPOC_v244/BP_Gahyeon_AnimationPOC_v244"
)
MAP = "/Game/Gahyeon/CharacterPipeline/v335/QA/L_GahyeonHairShadowCompare_v335"
SEQUENCE_ROOT = "/Game/Gahyeon/CharacterPipeline/v336/Sequence"
SEQUENCE_NAME = "LS_GahyeonHairShadowCompare_v336"
SEQUENCE = f"{SEQUENCE_ROOT}/{SEQUENCE_NAME}"
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v335-gahyeon-hair-shadow-build/report.json"
)
FACE_CENTER_Z = 152.23505401611328
FACE_HEIGHT_CM = 48.90284729003906


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


def component_named(actor, component_class, name):
    return next(
        component for component in actor.get_components_by_class(component_class)
        if str(component.get_name()) == name
    )


def build_gahyeon_hair_shadow_qa_v335():
    for path in (MAP, SEQUENCE):
        if unreal.EditorAssetLibrary.does_asset_exist(path):
            raise RuntimeError(f"refusing to overwrite immutable asset: {path}")
    actor_class = unreal.EditorAssetLibrary.load_blueprint_class(BLUEPRINT)
    if actor_class is None:
        raise RuntimeError(f"blueprint class unavailable: {BLUEPRINT}")
    if not unreal.EditorLevelLibrary.new_level(MAP):
        raise RuntimeError("failed to create hair shadow comparison map")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    cases = []
    for label, x, hair_visible in (
        ("Gahyeon_HairOn_v335", -42.0, True),
        ("Gahyeon_HairOff_v335", 42.0, False),
    ):
        actor = actors.spawn_actor_from_class(actor_class, unreal.Vector(x, 0.0, 0.0))
        if actor is None:
            raise RuntimeError(f"failed to spawn {label}")
        actor.set_actor_label(label)
        hair = component_named(actor, unreal.GroomComponent, "Hair")
        hair.set_visibility(hair_visible, True)
        hair.set_hidden_in_game(not hair_visible, True)
        cases.append((label, actor, hair, hair_visible))
    target = unreal.Vector(0.0, 0.0, FACE_CENTER_Z - 4.0)
    camera_location = target + unreal.Vector(0.0, 340.0, 0.0)
    camera = actors.spawn_actor_from_class(
        unreal.CineCameraActor,
        camera_location,
        unreal.MathLibrary.find_look_at_rotation(camera_location, target),
    )
    if camera is None:
        raise RuntimeError("failed to spawn hair comparison camera")
    camera.set_actor_label("CAM_GahyeonHairShadow_v335")
    camera.set_editor_property("auto_activate_for_player", unreal.AutoReceiveInput.PLAYER0)
    camera.camera_component.set_editor_property("current_focal_length", 85.0)
    camera.camera_component.set_editor_property("current_aperture", 8.0)
    add_rect_light(
        actors, "KEY_GahyeonHairShadow_v335", target + unreal.Vector(-110, 170, 65), target, 4400.0
    )
    add_rect_light(
        actors, "FILL_GahyeonHairShadow_v335", target + unreal.Vector(120, 150, 20), target, 2800.0
    )
    add_rect_light(
        actors, "RIM_GahyeonHairShadow_v335", target + unreal.Vector(0, -110, 50), target, 3000.0
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
        raise RuntimeError("failed to save hair shadow comparison map")
    sequence = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        SEQUENCE_NAME, SEQUENCE_ROOT, unreal.LevelSequence, unreal.LevelSequenceFactoryNew()
    )
    if sequence is None:
        raise RuntimeError("failed to create hair comparison sequence")
    sequence.set_display_rate(unreal.FrameRate(30, 1))
    sequence.set_tick_resolution(unreal.FrameRate(24000, 1))
    sequence.set_playback_start(0)
    sequence.set_playback_end(5)
    if not unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(sequence):
        raise RuntimeError("failed to open hair comparison sequence")
    camera_binding = unreal.get_editor_subsystem(
        unreal.LevelSequenceEditorSubsystem
    ).add_actors([camera])[0]
    camera_cut = sequence.add_track(unreal.MovieSceneCameraCutTrack).add_section()
    camera_cut.set_range(0, 5)
    binding_id = unreal.MovieSceneObjectBindingID()
    binding_id.set_editor_property("guid", camera_binding.get_id())
    camera_cut.set_camera_binding_id(binding_id)
    if not unreal.EditorAssetLibrary.save_loaded_asset(sequence, only_if_is_dirty=False):
        raise RuntimeError("failed to save hair comparison sequence")
    report = {
        "schemaVersion": 1,
        "iterations": ["v335", "v336"],
        "status": "draft-persistent-hair-comparison-ready",
        "map": MAP,
        "sequence": SEQUENCE,
        "blueprint": BLUEPRINT,
        "cases": [
            {"label": label, "hairVisible": visible}
            for label, _, _, visible in cases
        ],
        "faceHeightsCm": [FACE_HEIGHT_CM, FACE_HEIGHT_CM],
        "cameraTargetZ": FACE_CENTER_Z - 4.0,
        "hypothesis": (
            "If the dark neck patch is absent only when the Hair GroomComponent is "
            "hidden, Groom shadowing or AO is the primary defect rather than body normals."
        ),
        "visualValidationPending": True,
        "humanApproved": False,
        "productionReady": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("GAHYEON_V335_HAIR=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


build_gahyeon_hair_shadow_qa_v335()
