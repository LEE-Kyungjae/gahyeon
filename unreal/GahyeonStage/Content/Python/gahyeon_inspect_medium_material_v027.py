"""Log material parameters used by the assembled v027 MetaHuman."""

import unreal


MATERIAL_PATHS = (
    "/Game/Gahyeon/CharacterPipeline/v027/AssembledMedium/Skotukeda_Medium_v027/Face/Materials/MI_Face_Skin_Baked_LOD3",
    "/Game/Gahyeon/CharacterPipeline/v027/AssembledMedium/Skotukeda_Medium_v027/Face/Materials/MI_Face_Skin_Baked_LOD5to7",
    "/Game/Gahyeon/CharacterPipeline/v027/AssembledMedium/Skotukeda_Medium_v027/Body/Materials/MI_Body_Baked",
)


for material_path in MATERIAL_PATHS:
    material = unreal.EditorAssetLibrary.load_asset(material_path)
    if material is None:
        unreal.log_warning(f"missing material: {material_path}")
        continue
    unreal.log(f"GAHYEON_MATERIAL {material_path}")
    for parameter in unreal.MaterialEditingLibrary.get_texture_parameter_names(material):
        value = unreal.MaterialEditingLibrary.get_material_instance_texture_parameter_value(
            material, parameter
        )
        unreal.log(f"GAHYEON_TEXTURE_PARAMETER {parameter}={value.get_path_name() if value else 'None'}")

