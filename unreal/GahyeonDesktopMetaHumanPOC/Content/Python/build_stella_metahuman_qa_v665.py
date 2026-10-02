"""Build immutable fixed-lighting QA map for Stella MetaHuman v664."""

import json
from pathlib import Path

import unreal


MAP_PATH = "/Game/LivingCharacterPOC/v665/Preview/L_StellaMetaHumanQA_v665"
BLUEPRINT_PATH = (
    "/Game/LivingCharacterPOC/v664/AssembledMedium/"
    "StellaLily_MetaHumanMedium_v664/BP_StellaLily_MetaHumanMedium_v664"
)
CHARACTER_LABEL = "StellaLily_MetaHumanMedium_v664"
ASSEMBLY_RECEIPT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/"
    "living-character-poc-v664-stella-metahuman-assembly/assembly-receipt.json"
)
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/"
    "living-character-poc-v665-stella-metahuman-fixed-camera-qa/build-report.json"
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


def build_stella_metahuman_qa_v665():
    if REPORT.exists() or unreal.EditorAssetLibrary.does_asset_exist(MAP_PATH):
        raise RuntimeError("refusing to overwrite immutable v665 QA evidence")
    assembly = json.loads(ASSEMBLY_RECEIPT.read_text(encoding="utf-8"))
    if assembly.get("state") != "draft-medium-assembly-awaiting-fixed-camera-qa":
        raise RuntimeError("Stella v664 assembly lineage is not ready for QA")
    character_class = unreal.EditorAssetLibrary.load_blueprint_class(BLUEPRINT_PATH)
    if character_class is None:
        raise RuntimeError(f"Stella v664 Blueprint unavailable: {BLUEPRINT_PATH}")
    if not unreal.EditorLevelLibrary.new_level(MAP_PATH):
        raise RuntimeError(f"failed to create QA level: {MAP_PATH}")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    character = actors.spawn_actor_from_class(character_class, unreal.Vector())
    if character is None:
        raise RuntimeError("failed to spawn Stella v664 assembled MetaHuman")
    character.set_actor_label(CHARACTER_LABEL)
    origin, extent = character.get_actor_bounds(False, True)
    height = extent.z * 2.0
    if not 130.0 <= height <= 260.0:
        raise RuntimeError(f"unexpected assembled character height: {height}")

    face_target = unreal.Vector(origin.x, origin.y, origin.z + extent.z * 0.80)
    _rect_light(
        actors, "KEY_Stella_v665",
        face_target + unreal.Vector(-120.0, 180.0, 70.0), face_target,
        3500.0, 110.0, 110.0,
    )
    _rect_light(
        actors, "FILL_Stella_v665",
        face_target + unreal.Vector(130.0, 150.0, 25.0), face_target,
        1800.0, 100.0, 100.0,
    )
    _rect_light(
        actors, "RIM_Stella_v665",
        face_target + unreal.Vector(0.0, -130.0, 55.0), face_target,
        2400.0, 85.0, 100.0,
    )
    sky = actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector())
    sky.set_actor_label("SKY_Stella_v665")
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property(
        "intensity", 0.65
    )
    post = actors.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector())
    post.set_actor_label("PPV_Stella_v665")
    post.set_editor_property("unbound", True)
    settings = post.get_editor_property("settings")
    settings.set_editor_property("override_auto_exposure_method", True)
    settings.set_editor_property(
        "auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL
    )
    settings.set_editor_property("override_auto_exposure_bias", True)
    settings.set_editor_property("auto_exposure_bias", 1.0)
    settings.set_editor_property("override_motion_blur_amount", True)
    settings.set_editor_property("motion_blur_amount", 0.0)
    post.set_editor_property("settings", settings)
    if not unreal.EditorLevelLibrary.save_current_level():
        raise RuntimeError(f"failed to save QA level: {MAP_PATH}")
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v665",
        "state": "built-draft-fixed-lighting-qa-map",
        "engine": "5.8",
        "sourceAssembly": "v664",
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
    unreal.log(f"Stella v665 fixed-camera QA map saved: {MAP_PATH}")
    unreal.SystemLibrary.quit_editor()


build_stella_metahuman_qa_v665()
