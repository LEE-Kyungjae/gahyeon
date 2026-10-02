"""Duplicate v045 for a non-destructive fitted-garment silhouette test."""

import unreal


SOURCE_MAP = "/Game/Gahyeon/CharacterPipeline/v045/Preview/L_Skotukeda_DefaultGarment_v045"
TARGET_MAP = "/Game/Gahyeon/CharacterPipeline/v046/Preview/L_Skotukeda_FittedGarment_v046"

if unreal.EditorAssetLibrary.does_asset_exist(TARGET_MAP):
    raise RuntimeError(f"refusing to overwrite preview: {TARGET_MAP}")
preview = unreal.EditorAssetLibrary.duplicate_asset(SOURCE_MAP, TARGET_MAP)
if preview is None:
    raise RuntimeError(f"failed to duplicate preview map: {SOURCE_MAP}")
if not unreal.EditorAssetLibrary.save_loaded_asset(preview, only_if_is_dirty=False):
    raise RuntimeError(f"failed to save preview map: {TARGET_MAP}")
unreal.log(f"Gahyeon v046 fitted-garment preview duplicated: {TARGET_MAP}")
