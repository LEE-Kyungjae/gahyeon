"""Build an immutable v111b QA map with the verified Mac Groom card opacity."""

import json
from pathlib import Path

import unreal


SOURCE_MAP = "/Game/Gahyeon/CharacterPipeline/v104/Preview/L_Skotukeda_CardOpacity100_v104"
TARGET_MAP = "/Game/Gahyeon/CharacterPipeline/v112/Preview/L_Gahyeon_LowerFace_v112"
BLUEPRINT = (
    "/Game/Gahyeon/CharacterPipeline/v111b/AssembledHigh/"
    "Gahyeon_LowerFaceHigh_v111b/BP_Gahyeon_LowerFaceHigh_v111b"
)
SOURCE_MATERIAL = (
    "/Game/Gahyeon/CharacterPipeline/v111b/AssembledHigh/"
    "Gahyeon_LowerFaceHigh_v111b/Grooms/MI_WI_Hair_L_StraightBangs_Hair_Cards"
)
TARGET_MATERIAL = "/Game/Gahyeon/CharacterPipeline/v112/Materials/MI_Hair_Cards_Opacity100_v112"
OLD_LABEL = "Skotukeda_WardrobeGroomHigh_v095"
NEW_LABEL = "Gahyeon_LowerFaceHigh_v111b"
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v112-metahuman-lower-face-preview/build-report.json"
)


def build_lower_face_preview_v112():
    if REPORT.exists() or unreal.EditorAssetLibrary.does_asset_exist(TARGET_MAP):
        raise RuntimeError("refusing to overwrite immutable v112 preview")
    character_class = unreal.EditorAssetLibrary.load_blueprint_class(BLUEPRINT)
    if character_class is None:
        raise RuntimeError(f"v111b Blueprint unavailable: {BLUEPRINT}")
    material = unreal.EditorAssetLibrary.duplicate_asset(SOURCE_MATERIAL, TARGET_MATERIAL)
    if material is None:
        raise RuntimeError("failed to duplicate v111b Groom card material")
    for parameter in ("OpacityNear", "OpacityFar"):
        unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(material, parameter, 1.0)
        actual = unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(material, parameter)
        if abs(actual - 1.0) > 0.0001:
            raise RuntimeError(f"failed to verify {parameter}: {actual}")
    if not unreal.EditorAssetLibrary.save_loaded_asset(material, False):
        raise RuntimeError("failed to save v112 Groom card material")

    world = unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
    if world is None:
        raise RuntimeError(f"stable QA source map unavailable: {SOURCE_MAP}")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    old = next((actor for actor in actors.get_all_level_actors() if actor.get_actor_label() == OLD_LABEL), None)
    if old is None:
        raise RuntimeError(f"retained source actor unavailable: {OLD_LABEL}")
    location = old.get_actor_location()
    rotation = old.get_actor_rotation()
    actors.destroy_actor(old)
    character = actors.spawn_actor_from_class(character_class, location, rotation)
    if character is None:
        raise RuntimeError("failed to spawn v111b High Blueprint")
    character.set_actor_label(NEW_LABEL)
    hair = next(
        (component for component in character.get_components_by_class(unreal.GroomComponent)
         if component.get_name() == "Hair"),
        None,
    )
    if hair is None:
        raise RuntimeError("v111b Hair GroomComponent unavailable")
    hair.set_material(1, material)
    if hair.get_material(1).get_path_name() != material.get_path_name():
        raise RuntimeError("v112 card material override did not bind")
    if not unreal.EditorLoadingAndSavingUtils.save_map(world, TARGET_MAP):
        raise RuntimeError(f"failed to save v112 map: {TARGET_MAP}")

    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v112",
        "state": "built-draft-fixed-environment-preview",
        "engine": "5.8",
        "hypothesis": "The v111b lower-face assembly can be compared against v106 without reintroducing the Mac opacity-2.0 card expansion.",
        "action": "Place v111b in the retained v104 QA environment and bind a duplicated 1.0-opacity card material.",
        "expectedResult": "A stable draft map with the same environment and corrected Mac Groom presentation used by the retained baseline.",
        "baselineMap": SOURCE_MAP,
        "map": TARGET_MAP,
        "blueprint": BLUEPRINT,
        "characterLabel": NEW_LABEL,
        "material": material.get_path_name(),
        "opacityNear": 1.0,
        "opacityFar": 1.0,
        "sourceAssetsMutated": False,
        "automaticApproval": False,
        "productionReady": False,
    }, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v112 lower-face preview saved: {TARGET_MAP}")
    unreal.SystemLibrary.quit_editor()


build_lower_face_preview_v112()
