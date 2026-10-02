"""Build a fresh Skotukeda diagnostic with no wardrobe, BSP, or baked basewear."""

import json
from pathlib import Path

import unreal


MAP_PATH = "/Game/Gahyeon/CharacterPipeline/v235/Preview/L_Skotukeda_NoBasewearClean_v235"
BLUEPRINT_PATH = (
    "/Game/Gahyeon/CharacterPipeline/v027/AssembledMedium/"
    "Skotukeda_Medium_v027/BP_Skotukeda_Medium_v027"
)
BODY_MATERIAL_PATH = "/Game/Gahyeon/CharacterPipeline/v044/Materials/M_Body_SkinLit_v044"
FACE_MATERIAL_ROOT = "/Game/Gahyeon/CharacterPipeline/v235/Materials"
FACE_MATERIAL_NAME = "M_Face_CleanSkin_v235"
FACE_MATERIAL_PATH = f"{FACE_MATERIAL_ROOT}/{FACE_MATERIAL_NAME}"
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v235-skotukeda-no-basewear-clean/build-report.json"
)


def _create_clean_face_material():
    if unreal.EditorAssetLibrary.does_asset_exist(FACE_MATERIAL_PATH):
        raise RuntimeError(f"refusing to overwrite material: {FACE_MATERIAL_PATH}")
    material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        FACE_MATERIAL_NAME,
        FACE_MATERIAL_ROOT,
        unreal.Material,
        unreal.MaterialFactoryNew(),
    )
    if material is None:
        raise RuntimeError("failed to create clean face material")
    material.set_editor_property("used_with_skeletal_mesh", True)
    skin = unreal.MaterialEditingLibrary.create_material_expression(
        material, unreal.MaterialExpressionConstant3Vector, -420, -40
    )
    skin.set_editor_property("constant", unreal.LinearColor(0.545, 0.356, 0.314, 1.0))
    unreal.MaterialEditingLibrary.connect_material_property(
        skin, "", unreal.MaterialProperty.MP_BASE_COLOR
    )
    roughness = unreal.MaterialEditingLibrary.create_material_expression(
        material, unreal.MaterialExpressionConstant, -420, 120
    )
    roughness.set_editor_property("r", 0.58)
    unreal.MaterialEditingLibrary.connect_material_property(
        roughness, "", unreal.MaterialProperty.MP_ROUGHNESS
    )
    unreal.MaterialEditingLibrary.recompile_material(material)
    if not unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False):
        raise RuntimeError("failed to save clean face material")
    return material


def _rect_light(actors, label, location, target, intensity):
    light = actors.spawn_actor_from_class(
        unreal.RectLight,
        location,
        unreal.MathLibrary.find_look_at_rotation(location, target),
    )
    if light is None:
        raise RuntimeError(f"failed to spawn light: {label}")
    light.set_actor_label(label)
    component = light.get_component_by_class(unreal.RectLightComponent)
    component.set_editor_property("intensity", intensity)
    component.set_editor_property("source_width", 110.0)
    component.set_editor_property("source_height", 110.0)


def build_no_basewear_clean_scene_v235():
    if REPORT.exists() or unreal.EditorAssetLibrary.does_asset_exist(MAP_PATH):
        raise RuntimeError("refusing to overwrite immutable v235 output")
    character_class = unreal.EditorAssetLibrary.load_blueprint_class(BLUEPRINT_PATH)
    body_material = unreal.EditorAssetLibrary.load_asset(BODY_MATERIAL_PATH)
    if character_class is None or body_material is None:
        raise RuntimeError("approved Skotukeda Blueprint or clean Body material is unavailable")
    face_material = _create_clean_face_material()
    if not unreal.EditorLevelLibrary.new_level(MAP_PATH):
        raise RuntimeError(f"failed to create fresh empty map: {MAP_PATH}")

    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    character = actors.spawn_actor_from_class(character_class, unreal.Vector())
    if character is None:
        raise RuntimeError("failed to spawn approved Skotukeda Blueprint")
    character.set_actor_label("Skotukeda_NoBasewear_v235")

    changed_slots = []
    for component in character.get_components_by_class(unreal.SkeletalMeshComponent):
        if component.get_name() == "Body":
            component.set_material(0, body_material)
            changed_slots.append("Body:0")
        elif component.get_name() == "Face":
            component.set_material(6, face_material)
            component.set_material(7, face_material)
            changed_slots.extend(("Face:6", "Face:7"))
    if changed_slots != ["Body:0", "Face:6", "Face:7"]:
        raise RuntimeError(f"unexpected skin slot replacement result: {changed_slots}")

    target = unreal.Vector(0.0, 0.0, 95.0)
    camera_location = unreal.Vector(0.0, 430.0, 105.0)
    camera = actors.spawn_actor_from_class(
        unreal.CineCameraActor,
        camera_location,
        unreal.MathLibrary.find_look_at_rotation(camera_location, target),
    )
    if camera is None:
        raise RuntimeError("failed to spawn fixed full-body camera")
    camera.set_actor_label("CAM_Skotukeda_NoBasewear_v235")
    camera.set_editor_property("auto_activate_for_player", unreal.AutoReceiveInput.PLAYER0)
    camera.camera_component.set_editor_property("current_focal_length", 50.0)
    camera.camera_component.set_editor_property("current_aperture", 5.6)

    _rect_light(actors, "KEY_v235", unreal.Vector(-120.0, 220.0, 190.0), target, 3600.0)
    _rect_light(actors, "FILL_v235", unreal.Vector(130.0, 180.0, 155.0), target, 1900.0)
    _rect_light(actors, "RIM_v235", unreal.Vector(0.0, -150.0, 190.0), target, 2300.0)
    sky = actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector())
    sky.set_actor_label("SKY_v235")
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("intensity", 0.65)

    post = actors.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector())
    post.set_actor_label("PPV_v235")
    post.set_editor_property("unbound", True)
    settings = post.get_editor_property("settings")
    settings.set_editor_property("override_auto_exposure_method", True)
    settings.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)
    settings.set_editor_property("override_auto_exposure_bias", True)
    settings.set_editor_property("auto_exposure_bias", 1.0)
    post.set_editor_property("settings", settings)

    if not unreal.EditorLevelLibrary.save_current_level():
        raise RuntimeError(f"failed to save fresh map: {MAP_PATH}")
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v235",
        "state": "built-draft-no-basewear-clean-scene",
        "sourceBlueprint": BLUEPRINT_PATH,
        "map": MAP_PATH,
        "freshEmptyMap": True,
        "bspOrForegroundGeometry": False,
        "wardrobeActors": [],
        "skinSlotOverrides": changed_slots,
        "faceGeometryModified": False,
        "faceDnaModified": False,
        "originalGroomComponentsPreserved": True,
        "diagnosticMaterialOnly": True,
        "automaticApproval": False,
        "productionReady": False,
    }, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v235 clean no-basewear map saved: {MAP_PATH}")
    unreal.SystemLibrary.quit_editor()


build_no_basewear_clean_scene_v235()
