"""Color-code Diana's two jacket slots to identify the shoulder intersection."""

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE_MAP = "/Game/Gahyeon/Character2/Diana/v410/Runtime/L_DianaMacRuntimeHighKeyClearance_v410"
OUTPUT_MAP = "/Game/Gahyeon/Character2/Diana/v415/QA/L_DianaShoulderSlotIsolation_v415"
REPORT = ROOT / "artifacts/gahyeon-ch/iterations/v415-diana-shoulder-slot-isolation/report.json"


def debug_material(name, color):
    path = f"/Game/Gahyeon/Character2/Diana/v415/QA/{name}"
    material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        name, "/Game/Gahyeon/Character2/Diana/v415/QA", unreal.Material, unreal.MaterialFactoryNew()
    )
    if material is None:
        raise RuntimeError(f"failed to create {path}")
    material.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    value = unreal.MaterialEditingLibrary.create_material_expression(
        material, unreal.MaterialExpressionConstant3Vector, -220, 0
    )
    value.set_editor_property("constant", color)
    unreal.MaterialEditingLibrary.connect_material_property(
        value, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR
    )
    unreal.MaterialEditingLibrary.recompile_material(material)
    unreal.EditorAssetLibrary.save_loaded_asset(material, False)
    return material, path


if unreal.EditorAssetLibrary.does_asset_exist(OUTPUT_MAP) or REPORT.exists():
    raise RuntimeError("refusing to overwrite immutable Diana v415 QA assets")
red, red_path = debug_material("M_Diana_Jacket1_Red_v415", unreal.LinearColor(1.0, 0.0, 0.0, 1.0))
green, green_path = debug_material("M_Diana_Jacket2_Green_v415", unreal.LinearColor(0.0, 1.0, 0.0, 1.0))
unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
characters = [actor for actor in actors if isinstance(actor, unreal.SkeletalMeshActor)]
if world is None or len(characters) != 1:
    raise RuntimeError("v410 character composition changed unexpectedly")
component = characters[0].get_component_by_class(unreal.SkeletalMeshComponent)
component.set_material(9, red)
component.set_material(13, green)
if not unreal.EditorLoadingAndSavingUtils.save_map(world, OUTPUT_MAP):
    raise RuntimeError("failed to save Diana v415 QA map")
report = {
    "schemaVersion": 1,
    "iteration": "v415-diana-shoulder-slot-isolation",
    "status": "diagnostic",
    "sourceMap": SOURCE_MAP,
    "map": OUTPUT_MAP,
    "legend": {"slot9": "red", "slot13": "green"},
    "materials": [red_path, green_path],
    "mutatedProductionAssets": [],
    "productionReady": False
}
REPORT.parent.mkdir(parents=True, exist_ok=False)
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.SystemLibrary.quit_editor()
