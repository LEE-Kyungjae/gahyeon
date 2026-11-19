"""Build an immutable fixed-lighting QA map for the v169 FaceBuilder MetaHuman."""

import json
from pathlib import Path

import unreal


MAP_PATH = "/Game/Gahyeon/CharacterPipeline/v171/Preview/L_FaceBuilderMediumQA_v171"
BLUEPRINT_PATH = (
    "/Game/Gahyeon/CharacterPipeline/v169/AssembledMedium/"
    "Gahyeon_FaceBuilderMedium_v169/BP_Gahyeon_FaceBuilderMedium_v169"
)
CHARACTER_LABEL = "Gahyeon_FaceBuilderMedium_v169"
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v171-metahuman-facebuilder-fixed-camera-qa/build-report.json"
)


def _rect_light(actors, label, location, target, intensity, width, height):
    light = actors.spawn_actor_from_class(
        unreal.RectLight,
        location,
        unreal.MathLibrary.find_look_at_rotation(location, target),
    )
    if light is None:
        raise RuntimeError(f"failed to spawn {label}")
    light.set_actor_label(label)
    component = light.get_component_by_class(unreal.RectLightComponent)
    component.set_editor_property("intensity", intensity)
    component.set_editor_property("source_width", width)
    component.set_editor_property("source_height", height)
    return light


def build_facebuilder_medium_qa_v171():
    if REPORT.exists() or unreal.EditorAssetLibrary.does_asset_exist(MAP_PATH):
        raise RuntimeError("refusing to overwrite immutable v171 QA map")
    character_class = unreal.EditorAssetLibrary.load_blueprint_class(BLUEPRINT_PATH)
    if character_class is None:
        raise RuntimeError(f"v169 Blueprint unavailable: {BLUEPRINT_PATH}")
    if not unreal.EditorLevelLibrary.new_level(MAP_PATH):
        raise RuntimeError(f"failed to create QA level: {MAP_PATH}")

    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    character = actors.spawn_actor_from_class(character_class, unreal.Vector())
    if character is None:
        raise RuntimeError("failed to spawn v169 assembled MetaHuman")
    character.set_actor_label(CHARACTER_LABEL)
    origin, extent = character.get_actor_bounds(False, True)
    height = extent.z * 2.0
    if not 130.0 <= height <= 260.0:
        raise RuntimeError(f"unexpected assembled character height: {height}")

    face_target = unreal.Vector(origin.x, origin.y, origin.z + extent.z * 0.80)
    _rect_light(
        actors, "KEY_FaceBuilder_v171",
        face_target + unreal.Vector(-120.0, 180.0, 70.0), face_target,
        18000.0, 110.0, 110.0,
    )
    _rect_light(
        actors, "FILL_FaceBuilder_v171",
        face_target + unreal.Vector(130.0, 150.0, 25.0), face_target,
        9000.0, 100.0, 100.0,
    )
    _rect_light(
        actors, "RIM_FaceBuilder_v171",
        face_target + unreal.Vector(0.0, -130.0, 55.0), face_target,
        12000.0, 85.0, 100.0,
    )
    sky = actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector())
    sky.set_actor_label("SKY_FaceBuilder_v171")
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("intensity", 0.65)

    post = actors.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector())
    post.set_actor_label("PPV_FaceBuilder_v171")
    post.set_editor_property("unbound", True)
    settings = post.get_editor_property("settings")
    settings.set_editor_property("override_auto_exposure_method", True)
    settings.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)
    settings.set_editor_property("override_auto_exposure_bias", True)
    settings.set_editor_property("auto_exposure_bias", 3.0)
    post.set_editor_property("settings", settings)

    if not unreal.EditorLevelLibrary.save_current_level():
        raise RuntimeError(f"failed to save QA level: {MAP_PATH}")
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v171",
        "state": "built-draft-fixed-lighting-qa-map",
        "engine": "5.8",
        "sourceAssembly": "v169",
        "map": MAP_PATH,
        "blueprint": BLUEPRINT_PATH,
        "characterLabel": CHARACTER_LABEL,
        "bounds": {
            "origin": [origin.x, origin.y, origin.z],
            "extent": [extent.x, extent.y, extent.z],
            "heightCm": height,
        },
        "automaticApproval": False,
        "productionReady": False,
    }, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v171 FaceBuilder Medium QA map saved: {MAP_PATH}")
    unreal.SystemLibrary.quit_editor()


build_facebuilder_medium_qa_v171()
