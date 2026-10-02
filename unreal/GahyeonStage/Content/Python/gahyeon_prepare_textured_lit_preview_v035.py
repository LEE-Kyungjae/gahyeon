"""Promote the v034 textured materials to skeletal-mesh-safe v035 assets."""

import unreal


SOURCE_MAP = "/Game/Gahyeon/CharacterPipeline/v034/Preview/L_Skotukeda_TexturedLit_v034"
TARGET_MAP = "/Game/Gahyeon/CharacterPipeline/v035/Preview/L_Skotukeda_TexturedLit_v035"
SOURCE_MATERIAL_ROOT = "/Game/Gahyeon/CharacterPipeline/v034/Materials"
TARGET_MATERIAL_ROOT = "/Game/Gahyeon/CharacterPipeline/v035/Materials"
MATERIAL_NAMES = (
    "M_Face_TexturedLit_v034",
    "M_Body_TexturedLit_v034",
)


asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
materials = {}
for source_name in MATERIAL_NAMES:
    target_name = source_name.replace("v034", "v035")
    source_path = f"{SOURCE_MATERIAL_ROOT}/{source_name}"
    target_path = f"{TARGET_MATERIAL_ROOT}/{target_name}"
    if unreal.EditorAssetLibrary.does_asset_exist(target_path):
        raise RuntimeError(f"refusing to overwrite material: {target_path}")
    material = asset_tools.duplicate_asset(
        target_name, TARGET_MATERIAL_ROOT, unreal.EditorAssetLibrary.load_asset(source_path)
    )
    if material is None:
        raise RuntimeError(f"failed to duplicate material: {source_path}")
    material.set_editor_property("used_with_skeletal_mesh", True)
    unreal.MaterialEditingLibrary.recompile_material(material)
    if not unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False):
        raise RuntimeError(f"failed to save material: {target_path}")
    materials[target_name] = material

if unreal.EditorAssetLibrary.does_asset_exist(TARGET_MAP):
    raise RuntimeError(f"refusing to overwrite preview: {TARGET_MAP}")
preview = unreal.EditorAssetLibrary.duplicate_asset(SOURCE_MAP, TARGET_MAP)
if preview is None:
    raise RuntimeError(f"failed to duplicate preview map: {SOURCE_MAP}")

world = unreal.EditorLoadingAndSavingUtils.load_map(TARGET_MAP)
if world is None:
    raise RuntimeError(f"failed to load preview map: {TARGET_MAP}")

replacements = 0
for actor in unreal.EditorLevelLibrary.get_all_level_actors():
    for component in actor.get_components_by_class(unreal.SkeletalMeshComponent):
        for slot_index in range(component.get_num_materials()):
            current = component.get_material(slot_index)
            if current is None:
                continue
            current_name = current.get_name()
            if current_name == "M_Face_TexturedLit_v034":
                component.set_material(slot_index, materials["M_Face_TexturedLit_v035"])
                replacements += 1
            elif current_name == "M_Body_TexturedLit_v034":
                component.set_material(slot_index, materials["M_Body_TexturedLit_v035"])
                replacements += 1

if replacements != 3:
    raise RuntimeError(f"expected 3 material replacements, got {replacements}")
unreal.EditorLevelLibrary.save_current_level()
unreal.log(f"Gahyeon v035 skeletal textured-lit preview saved: slots={replacements}")
