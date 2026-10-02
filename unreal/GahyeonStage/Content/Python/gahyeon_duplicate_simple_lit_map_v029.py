"""Duplicate v027 into an immutable simple-lit material diagnostic map."""

import unreal


SOURCE_MAP = "/Game/Gahyeon/CharacterPipeline/v027/Preview/L_Skotukeda_Medium_v027"
TARGET_MAP = "/Game/Gahyeon/CharacterPipeline/v029/Preview/L_Skotukeda_SimpleLit_v029"

if unreal.EditorAssetLibrary.does_asset_exist(TARGET_MAP):
    raise RuntimeError(f"refusing to overwrite preview: {TARGET_MAP}")
duplicated = unreal.EditorAssetLibrary.duplicate_asset(SOURCE_MAP, TARGET_MAP)
if duplicated is None:
    raise RuntimeError(f"failed to duplicate preview map: {SOURCE_MAP}")
if not unreal.EditorAssetLibrary.save_loaded_asset(duplicated, only_if_is_dirty=False):
    raise RuntimeError(f"failed to save preview map: {TARGET_MAP}")
unreal.log(f"Gahyeon v029 simple-lit map duplicated: {TARGET_MAP}")

