"""Prepare immutable v033 skin materials and map without loading the new map."""

import unreal


SOURCE_MAP = "/Game/Gahyeon/CharacterPipeline/v027/Preview/L_Skotukeda_Medium_v027"
TARGET_MAP = "/Game/Gahyeon/CharacterPipeline/v033/Preview/L_Skotukeda_FlatSkin_v033"
MATERIAL_ROOT = "/Game/Gahyeon/CharacterPipeline/v033/Materials"
COMMON = "/Game/Gahyeon/CharacterPipeline/v027/CommonMedium/Lookdev_UHM/Common/Textures/Placeholders"
FLAT_NORMAL = f"{COMMON}/T_Flat_N"
FLAT_BLACK = f"{COMMON}/T_Flat_Black_M"
FLAT_WHITE = f"{COMMON}/T_Flat_White_C"
SOURCE_MATERIALS = (
    "/Game/Gahyeon/CharacterPipeline/v027/AssembledMedium/Skotukeda_Medium_v027/Face/Materials/MI_Face_Skin_Baked_LOD3",
    "/Game/Gahyeon/CharacterPipeline/v027/AssembledMedium/Skotukeda_Medium_v027/Face/Materials/MI_Face_Skin_Baked_LOD5to7",
    "/Game/Gahyeon/CharacterPipeline/v027/AssembledMedium/Skotukeda_Medium_v027/Body/Materials/MI_Body_Baked",
)


flat_normal = unreal.EditorAssetLibrary.load_asset(FLAT_NORMAL)
flat_black = unreal.EditorAssetLibrary.load_asset(FLAT_BLACK)
flat_white = unreal.EditorAssetLibrary.load_asset(FLAT_WHITE)
if any(texture is None for texture in (flat_normal, flat_black, flat_white)):
    raise RuntimeError("one or more flat diagnostic textures are unavailable")

for source_path in SOURCE_MATERIALS:
    name = source_path.rsplit("/", 1)[-1]
    target_path = f"{MATERIAL_ROOT}/{name}_FlatSkin_v033"
    if unreal.EditorAssetLibrary.does_asset_exist(target_path):
        raise RuntimeError(f"refusing to overwrite material: {target_path}")
    material = unreal.EditorAssetLibrary.duplicate_asset(source_path, target_path)
    if material is None:
        raise RuntimeError(f"failed to duplicate material: {source_path}")
    for parameter in (
        "Normal Baked",
        "Normal LOD Baked",
        "Micro Skin Details Normal",
        "Bent Normal",
    ):
        unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(
            material, parameter, flat_normal
        )
    unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(
        material, "SRMF Baked", flat_black
    )
    unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(
        material, "Scatter Baked", flat_white
    )
    if not unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False):
        raise RuntimeError(f"failed to save material: {target_path}")

if unreal.EditorAssetLibrary.does_asset_exist(TARGET_MAP):
    raise RuntimeError(f"refusing to overwrite preview: {TARGET_MAP}")
duplicated_map = unreal.EditorAssetLibrary.duplicate_asset(SOURCE_MAP, TARGET_MAP)
if duplicated_map is None:
    raise RuntimeError(f"failed to duplicate preview map: {SOURCE_MAP}")
if not unreal.EditorAssetLibrary.save_loaded_asset(
    duplicated_map, only_if_is_dirty=False
):
    raise RuntimeError(f"failed to save preview map: {TARGET_MAP}")
unreal.log(f"Gahyeon v033 flat-skin assets prepared: {TARGET_MAP}")

