"""Duplicate the framed v031 map for a clean runtime full-body view."""

import unreal


SOURCE_MAP = "/Game/Gahyeon/CharacterPipeline/v031/Preview/L_Skotukeda_FullBody_v031"
TARGET_MAP = "/Game/Gahyeon/CharacterPipeline/v032/Preview/L_Skotukeda_FullBodyClean_v032"

if unreal.EditorAssetLibrary.does_asset_exist(TARGET_MAP):
    raise RuntimeError(f"refusing to overwrite preview: {TARGET_MAP}")
duplicated = unreal.EditorAssetLibrary.duplicate_asset(SOURCE_MAP, TARGET_MAP)
if duplicated is None:
    raise RuntimeError(f"failed to duplicate preview map: {SOURCE_MAP}")
if not unreal.EditorAssetLibrary.save_loaded_asset(duplicated, only_if_is_dirty=False):
    raise RuntimeError(f"failed to save preview map: {TARGET_MAP}")
unreal.log(f"Gahyeon v032 clean full-body map duplicated: {TARGET_MAP}")

