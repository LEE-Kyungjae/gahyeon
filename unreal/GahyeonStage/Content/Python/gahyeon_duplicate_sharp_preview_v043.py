"""Duplicate v042 for a sharp, deterministic desktop QA render."""

import unreal


SOURCE_MAP = "/Game/Gahyeon/CharacterPipeline/v042/Preview/L_Skotukeda_NoBangsPOC_v042"
TARGET_MAP = "/Game/Gahyeon/CharacterPipeline/v043/Preview/L_Skotukeda_SharpPOC_v043"

if unreal.EditorAssetLibrary.does_asset_exist(TARGET_MAP):
    raise RuntimeError(f"refusing to overwrite preview: {TARGET_MAP}")
preview = unreal.EditorAssetLibrary.duplicate_asset(SOURCE_MAP, TARGET_MAP)
if preview is None:
    raise RuntimeError(f"failed to duplicate preview map: {SOURCE_MAP}")
if not unreal.EditorAssetLibrary.save_loaded_asset(preview, only_if_is_dirty=False):
    raise RuntimeError(f"failed to save preview map: {TARGET_MAP}")
unreal.log(f"Gahyeon v043 sharp preview duplicated: {TARGET_MAP}")
