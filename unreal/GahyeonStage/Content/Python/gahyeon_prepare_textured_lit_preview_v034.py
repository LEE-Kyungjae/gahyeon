"""Create simple textured Default Lit skin materials and a v034 QA map."""

import unreal


SOURCE_MAP = "/Game/Gahyeon/CharacterPipeline/v027/Preview/L_Skotukeda_Medium_v027"
TARGET_MAP = "/Game/Gahyeon/CharacterPipeline/v034/Preview/L_Skotukeda_TexturedLit_v034"
MATERIAL_ROOT = "/Game/Gahyeon/CharacterPipeline/v034/Materials"
TEXTURES = {
    "M_Face_TexturedLit_v034": (
        "/Game/Gahyeon/CharacterPipeline/v027/AssembledMedium/Skotukeda_Medium_v027/"
        "Face/Baked/T_Head_LOD3_BC"
    ),
    "M_Body_TexturedLit_v034": (
        "/Game/Gahyeon/CharacterPipeline/v027/AssembledMedium/Skotukeda_Medium_v027/"
        "Body/Baked/T_Body_BC"
    ),
}


asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
for material_name, texture_path in TEXTURES.items():
    asset_path = f"{MATERIAL_ROOT}/{material_name}"
    if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        raise RuntimeError(f"refusing to overwrite material: {asset_path}")
    texture = unreal.EditorAssetLibrary.load_asset(texture_path)
    if texture is None:
        raise RuntimeError(f"base-color texture is unavailable: {texture_path}")
    material = asset_tools.create_asset(
        material_name, MATERIAL_ROOT, unreal.Material, unreal.MaterialFactoryNew()
    )
    if material is None:
        raise RuntimeError(f"failed to create material: {asset_path}")
    sample = unreal.MaterialEditingLibrary.create_material_expression(
        material, unreal.MaterialExpressionTextureSample, -420, -40
    )
    sample.set_editor_property("texture", texture)
    if not unreal.MaterialEditingLibrary.connect_material_property(
        sample, "RGB", unreal.MaterialProperty.MP_BASE_COLOR
    ):
        raise RuntimeError(f"failed to connect base color: {material_name}")
    roughness = unreal.MaterialEditingLibrary.create_material_expression(
        material, unreal.MaterialExpressionConstant, -420, 120
    )
    roughness.set_editor_property("r", 0.55)
    if not unreal.MaterialEditingLibrary.connect_material_property(
        roughness, "", unreal.MaterialProperty.MP_ROUGHNESS
    ):
        raise RuntimeError(f"failed to connect roughness: {material_name}")
    unreal.MaterialEditingLibrary.recompile_material(material)
    if not unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False):
        raise RuntimeError(f"failed to save material: {asset_path}")

if unreal.EditorAssetLibrary.does_asset_exist(TARGET_MAP):
    raise RuntimeError(f"refusing to overwrite preview: {TARGET_MAP}")
duplicated = unreal.EditorAssetLibrary.duplicate_asset(SOURCE_MAP, TARGET_MAP)
if duplicated is None:
    raise RuntimeError(f"failed to duplicate preview map: {SOURCE_MAP}")
if not unreal.EditorAssetLibrary.save_loaded_asset(duplicated, only_if_is_dirty=False):
    raise RuntimeError(f"failed to save preview map: {TARGET_MAP}")
unreal.log(f"Gahyeon v034 textured-lit assets prepared: {TARGET_MAP}")

