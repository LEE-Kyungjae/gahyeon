"""Duplicate stable v036 for a MetaHuman hair-cards runtime POC."""

import unreal


SOURCE_MAP = "/Game/Gahyeon/CharacterPipeline/v036/Preview/L_Skotukeda_BalancedFullBody_v036"
TARGET_MAP = "/Game/Gahyeon/CharacterPipeline/v038/Preview/L_Skotukeda_HairCardsPOC_v038"

if unreal.EditorAssetLibrary.does_asset_exist(TARGET_MAP):
    raise RuntimeError(f"refusing to overwrite preview: {TARGET_MAP}")
preview = unreal.EditorAssetLibrary.duplicate_asset(SOURCE_MAP, TARGET_MAP)
if preview is None:
    raise RuntimeError(f"failed to duplicate preview map: {SOURCE_MAP}")
if not unreal.EditorAssetLibrary.save_loaded_asset(preview, only_if_is_dirty=False):
    raise RuntimeError(f"failed to save preview map: {TARGET_MAP}")
unreal.log(f"Gahyeon v038 hair-cards preview duplicated: {TARGET_MAP}")
