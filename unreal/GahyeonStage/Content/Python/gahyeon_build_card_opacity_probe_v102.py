"""Build an immutable low-opacity Groom card probe from the official High assembly."""

import json
from pathlib import Path

import unreal


SOURCE_MAP = "/Game/Gahyeon/CharacterPipeline/v096/Preview/L_Skotukeda_WardrobeGroomHigh_v096"
TARGET_MAP = "/Game/Gahyeon/CharacterPipeline/v102b/Preview/L_Skotukeda_CardOpacityProbe_v102b"
SOURCE_MATERIAL = (
    "/Game/Gahyeon/CharacterPipeline/v095/AssembledHigh/"
    "Skotukeda_WardrobeGroomHigh_v095/Grooms/"
    "MI_WI_Hair_L_StraightBangs_Hair_Cards"
)
TARGET_MATERIAL = "/Game/Gahyeon/CharacterPipeline/v102b/Materials/MI_Hair_Cards_Opacity035_v102b"
LABEL = "Skotukeda_WardrobeGroomHigh_v095"
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v102b-groom-card-opacity-probe/build-report.json"
)


def build_card_opacity_probe():
    if REPORT.exists() or unreal.EditorAssetLibrary.does_asset_exist(TARGET_MAP):
        raise RuntimeError("refusing to overwrite immutable v102b probe")
    material = unreal.EditorAssetLibrary.duplicate_asset(SOURCE_MATERIAL, TARGET_MATERIAL)
    if material is None:
        raise RuntimeError("failed to duplicate official Groom card material")
    for parameter in ("OpacityNear", "OpacityFar"):
        unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(material, parameter, 0.35)
        actual = unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(material, parameter)
        if abs(actual - 0.35) > 0.0001:
            raise RuntimeError(f"failed to verify {parameter}: {actual}")
    unreal.EditorAssetLibrary.save_loaded_asset(material, False)
    world = unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
    if world is None:
        raise RuntimeError(f"source map unavailable: {SOURCE_MAP}")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    character = next((actor for actor in actors.get_all_level_actors() if actor.get_actor_label() == LABEL), None)
    if character is None:
        raise RuntimeError(f"High character unavailable: {LABEL}")
    hair = next((component for component in character.get_components_by_class(unreal.GroomComponent) if component.get_name() == "Hair"), None)
    if hair is None:
        raise RuntimeError("Hair GroomComponent unavailable")
    hair.set_material(1, material)
    if hair.get_material(1).get_path_name() != material.get_path_name():
        raise RuntimeError("card material override did not bind")
    if not unreal.EditorLoadingAndSavingUtils.save_map(world, TARGET_MAP):
        raise RuntimeError(f"failed to save probe map: {TARGET_MAP}")
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v102b",
        "state": "built-diagnostic-groom-card-opacity-probe",
        "hypothesis": "The official 2.0 near/far opacity multipliers over-expand Layout2 card coverage on the Mac card path.",
        "sourceMap": SOURCE_MAP,
        "map": TARGET_MAP,
        "sourceMaterial": SOURCE_MATERIAL,
        "material": material.get_path_name(),
        "opacityNear": 0.35,
        "opacityFar": 0.35,
        "automaticApproval": False,
        "productionReady": False,
    }, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v102 Groom card opacity probe saved: {TARGET_MAP}")
    unreal.SystemLibrary.quit_editor()


build_card_opacity_probe()
