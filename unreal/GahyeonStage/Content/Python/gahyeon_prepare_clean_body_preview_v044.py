"""Create a clean skin-only body material and duplicate the sharp v043 map."""

import unreal


SOURCE_MAP = "/Game/Gahyeon/CharacterPipeline/v043/Preview/L_Skotukeda_SharpPOC_v043"
TARGET_MAP = "/Game/Gahyeon/CharacterPipeline/v044/Preview/L_Skotukeda_CleanBody_v044"
MATERIAL_ROOT = "/Game/Gahyeon/CharacterPipeline/v044/Materials"
MATERIAL_NAME = "M_Body_SkinLit_v044"
MATERIAL_PATH = f"{MATERIAL_ROOT}/{MATERIAL_NAME}"

asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
if unreal.EditorAssetLibrary.does_asset_exist(MATERIAL_PATH):
    raise RuntimeError(f"refusing to overwrite material: {MATERIAL_PATH}")
material = asset_tools.create_asset(
    MATERIAL_NAME, MATERIAL_ROOT, unreal.Material, unreal.MaterialFactoryNew()
)
if material is None:
    raise RuntimeError(f"failed to create material: {MATERIAL_PATH}")
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
    raise RuntimeError(f"failed to save material: {MATERIAL_PATH}")

if unreal.EditorAssetLibrary.does_asset_exist(TARGET_MAP):
    raise RuntimeError(f"refusing to overwrite preview: {TARGET_MAP}")
preview = unreal.EditorAssetLibrary.duplicate_asset(SOURCE_MAP, TARGET_MAP)
if preview is None:
    raise RuntimeError(f"failed to duplicate preview map: {SOURCE_MAP}")
if not unreal.EditorAssetLibrary.save_loaded_asset(preview, only_if_is_dirty=False):
    raise RuntimeError(f"failed to save preview map: {TARGET_MAP}")
unreal.log(f"Gahyeon v044 clean-body assets prepared: {TARGET_MAP}")
