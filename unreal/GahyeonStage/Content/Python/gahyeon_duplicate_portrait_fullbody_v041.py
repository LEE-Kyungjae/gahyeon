"""Duplicate v040 for the measured portrait full-body framing correction."""

import unreal


SOURCE_MAP = "/Game/Gahyeon/CharacterPipeline/v040/Preview/L_Skotukeda_PortraitPOC_v040"
TARGET_MAP = "/Game/Gahyeon/CharacterPipeline/v041/Preview/L_Skotukeda_PortraitFullBody_v041"

if unreal.EditorAssetLibrary.does_asset_exist(TARGET_MAP):
    raise RuntimeError(f"refusing to overwrite preview: {TARGET_MAP}")
preview = unreal.EditorAssetLibrary.duplicate_asset(SOURCE_MAP, TARGET_MAP)
if preview is None:
    raise RuntimeError(f"failed to duplicate preview map: {SOURCE_MAP}")
if not unreal.EditorAssetLibrary.save_loaded_asset(preview, only_if_is_dirty=False):
    raise RuntimeError(f"failed to save preview map: {TARGET_MAP}")
unreal.log(f"Gahyeon v041 portrait full-body preview duplicated: {TARGET_MAP}")
