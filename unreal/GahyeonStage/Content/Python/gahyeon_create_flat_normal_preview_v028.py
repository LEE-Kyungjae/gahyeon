"""Create a non-destructive v028 preview with flat skin normal overrides."""

import unreal


SOURCE_MAP = "/Game/Gahyeon/CharacterPipeline/v027/Preview/L_Skotukeda_Medium_v027"
TARGET_MAP = "/Game/Gahyeon/CharacterPipeline/v028/Preview/L_Skotukeda_FlatNormal_v028"
MATERIAL_ROOT = "/Game/Gahyeon/CharacterPipeline/v028/Materials"
FLAT_NORMAL_PATH = (
    "/Game/Gahyeon/CharacterPipeline/v027/CommonMedium/Lookdev_UHM/Common/"
    "Textures/Placeholders/T_Flat_N"
)
SOURCE_MATERIALS = (
    "/Game/Gahyeon/CharacterPipeline/v027/AssembledMedium/Skotukeda_Medium_v027/"
    "Face/Materials/MI_Face_Skin_Baked_LOD3",
    "/Game/Gahyeon/CharacterPipeline/v027/AssembledMedium/Skotukeda_Medium_v027/"
    "Face/Materials/MI_Face_Skin_Baked_LOD5to7",
    "/Game/Gahyeon/CharacterPipeline/v027/AssembledMedium/Skotukeda_Medium_v027/"
    "Body/Materials/MI_Body_Baked",
)
NORMAL_PARAMETERS = (
    "Normal Baked",
    "Normal LOD Baked",
    "Micro Skin Details Normal",
    "Bent Normal",
)


def create_flat_normal_preview():
    if unreal.EditorAssetLibrary.does_asset_exist(TARGET_MAP):
        raise RuntimeError(f"refusing to overwrite preview: {TARGET_MAP}")
    flat_normal = unreal.EditorAssetLibrary.load_asset(FLAT_NORMAL_PATH)
    if flat_normal is None:
        raise RuntimeError(f"flat normal texture is unavailable: {FLAT_NORMAL_PATH}")

    replacements = {}
    for source_path in SOURCE_MATERIALS:
        target_path = f"{MATERIAL_ROOT}/{source_path.rsplit('/', 1)[-1]}_FlatNormal_v028"
        duplicate = unreal.EditorAssetLibrary.duplicate_asset(source_path, target_path)
        if duplicate is None:
            raise RuntimeError(f"failed to duplicate material: {source_path}")
        for parameter in NORMAL_PARAMETERS:
            unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(
                duplicate, parameter, flat_normal
            )
        unreal.EditorAssetLibrary.save_loaded_asset(duplicate, only_if_is_dirty=False)
        replacements[source_path] = duplicate

    if unreal.EditorAssetLibrary.duplicate_asset(SOURCE_MAP, TARGET_MAP) is None:
        raise RuntimeError(f"failed to duplicate preview map: {SOURCE_MAP}")
    if not unreal.EditorLevelLibrary.load_level(TARGET_MAP):
        raise RuntimeError(f"failed to load preview map: {TARGET_MAP}")

    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    replaced_slots = 0
    for actor in actors.get_all_level_actors():
        for component in actor.get_components_by_class(unreal.MeshComponent):
            for slot in range(component.get_num_materials()):
                material = component.get_material(slot)
                if material is None:
                    continue
                replacement = replacements.get(material.get_path_name())
                if replacement is not None:
                    component.set_material(slot, replacement)
                    replaced_slots += 1
    if replaced_slots == 0:
        raise RuntimeError("no assembled skin material slots were replaced")
    if not unreal.EditorLevelLibrary.save_current_level():
        raise RuntimeError(f"failed to save flat-normal preview: {TARGET_MAP}")
    unreal.log(
        f"Gahyeon v028 flat-normal preview saved: slots={replaced_slots} map={TARGET_MAP}"
    )


create_flat_normal_preview()
