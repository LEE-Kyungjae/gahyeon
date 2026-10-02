"""Duplicate the v027 QA map without loading it in the same editor process."""

import unreal


SOURCE_MAP = "/Game/Gahyeon/CharacterPipeline/v027/Preview/L_Skotukeda_Medium_v027"
TARGET_MAP = "/Game/Gahyeon/CharacterPipeline/v028/Preview/L_Skotukeda_FlatNormal_v028"

if unreal.EditorAssetLibrary.does_asset_exist(TARGET_MAP):
    raise RuntimeError(f"refusing to overwrite preview: {TARGET_MAP}")
duplicated_map = unreal.EditorAssetLibrary.duplicate_asset(SOURCE_MAP, TARGET_MAP)
if duplicated_map is None:
    raise RuntimeError(f"failed to duplicate preview map: {SOURCE_MAP}")
if not unreal.EditorAssetLibrary.save_loaded_asset(
    duplicated_map, only_if_is_dirty=False
):
    raise RuntimeError(f"failed to save duplicated preview map: {TARGET_MAP}")
unreal.log(f"Gahyeon v028 map duplicated: {TARGET_MAP}")
