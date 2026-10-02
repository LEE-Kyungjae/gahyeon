"""Create v025 using only Identity head geometry and template eyes/teeth/body."""

import unreal


SOURCE_CHARACTER = "/Game/Fab/MetaHuman/Skotukeda"
IDENTITY_ASSET = "/Game/Gahyeon/CharacterPipeline/v024/Identity/MHI_Gahyeon_v024"
TARGET_CHARACTER = "/Game/Gahyeon/CharacterPipeline/v025/Character/MHC_Gahyeon_HeadOnlyPOC_v025"


def conform_head_only_v025():
    if unreal.EditorAssetLibrary.does_asset_exist(TARGET_CHARACTER):
        raise RuntimeError(f"refusing to overwrite existing iteration: {TARGET_CHARACTER}")
    character = unreal.EditorAssetLibrary.duplicate_asset(SOURCE_CHARACTER, TARGET_CHARACTER)
    identity = unreal.EditorAssetLibrary.load_asset(IDENTITY_ASSET)
    if character is None or identity is None:
        raise RuntimeError("source MetaHuman Character or conformed Identity is unavailable")
    try:
        call_result = unreal.GahyeonMetaHumanQALibrary.conform_character_from_identity(
            character, identity, False, False
        )
        result = bool(call_result[0]) if isinstance(call_result, tuple) else bool(call_result)
        message = str(call_result[-1]) if isinstance(call_result, tuple) else ""
        unreal.log(f"Gahyeon v025 head-only conform: success={result} message={message}")
        if not result:
            raise RuntimeError(f"head-only MetaHuman conform failed: {message}")
        if not unreal.EditorAssetLibrary.save_loaded_asset(character, only_if_is_dirty=False):
            raise RuntimeError(f"failed to save v025 character: {TARGET_CHARACTER}")
    except Exception:
        unreal.EditorAssetLibrary.delete_asset(TARGET_CHARACTER)
        raise


conform_head_only_v025()
