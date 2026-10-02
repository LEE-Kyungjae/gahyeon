"""Create a non-approved coarse MetaHuman Character POC from solved Identity v024."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import unreal


SOURCE_CHARACTER = "/Game/Fab/MetaHuman/Skotukeda"
IDENTITY_ASSET = "/Game/Gahyeon/CharacterPipeline/v024/Identity/MHI_Gahyeon_v024"
TARGET_CHARACTER = "/Game/Gahyeon/CharacterPipeline/v024/Character/MHC_Gahyeon_CoarsePOC_v024"


def conform_coarse_identity_v024():
    workspace = Path(os.environ.get("GAHYEON_WORKSPACE", "/Users/ze/work/gahyeonbot"))
    receipt_path = workspace / "artifacts/gahyeon-ch/metahuman-coarse-poc-v024.json"

    if unreal.EditorAssetLibrary.does_asset_exist(TARGET_CHARACTER):
        raise RuntimeError(f"refusing to overwrite existing character iteration: {TARGET_CHARACTER}")
    if not unreal.EditorAssetLibrary.does_asset_exist(SOURCE_CHARACTER):
        raise RuntimeError(f"source MetaHuman Character is unavailable: {SOURCE_CHARACTER}")
    if not unreal.EditorAssetLibrary.does_asset_exist(IDENTITY_ASSET):
        raise RuntimeError(f"solved MetaHuman Identity is unavailable: {IDENTITY_ASSET}")

    duplicated = unreal.EditorAssetLibrary.duplicate_asset(SOURCE_CHARACTER, TARGET_CHARACTER)
    if duplicated is None:
        raise RuntimeError(f"failed to duplicate source MetaHuman Character: {SOURCE_CHARACTER}")

    character = unreal.EditorAssetLibrary.load_asset(TARGET_CHARACTER)
    identity = unreal.EditorAssetLibrary.load_asset(IDENTITY_ASSET)
    try:
        call_result = unreal.GahyeonMetaHumanQALibrary.conform_character_from_identity(
            character, identity, True, True
        )
        if isinstance(call_result, tuple):
            result = bool(call_result[0])
            message = str(call_result[-1])
        else:
            result = bool(call_result)
            message = "bridge returned no diagnostic message"
        unreal.log(f"Gahyeon coarse MetaHuman conform: success={result} message={message}")
        if not result:
            raise RuntimeError(f"MetaHuman Character identity conform failed: {message}")
        if not unreal.EditorAssetLibrary.save_loaded_asset(character, only_if_is_dirty=False):
            raise RuntimeError(f"failed to save conformed character: {TARGET_CHARACTER}")
        unreal.EditorAssetLibrary.sync_browser_to_objects([TARGET_CHARACTER])
    except Exception:
        unreal.EditorAssetLibrary.delete_asset(TARGET_CHARACTER)
        raise

    identity_file = workspace / "unreal/GahyeonStage/Content/Gahyeon/CharacterPipeline/v024/Identity/MHI_Gahyeon_v024.uasset"
    character_file = workspace / "unreal/GahyeonStage/Content/Gahyeon/CharacterPipeline/v024/Character/MHC_Gahyeon_CoarsePOC_v024.uasset"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "observedAt": datetime.now(timezone.utc).isoformat(),
                "iteration": "v024",
                "engine": "Unreal Engine 5.8",
                "sourceCharacter": SOURCE_CHARACTER,
                "identityAsset": IDENTITY_ASSET,
                "targetCharacter": TARGET_CHARACTER,
                "identityFileExists": identity_file.is_file(),
                "characterFileExists": character_file.is_file(),
                "markerAuthority": "default-neutral-contours-not-human-corrected",
                "qualityStage": "coarse-poc",
                "automaticApproval": False,
                "identityApproved": False,
                "productionReady": False,
                "aaaQualityClaim": False,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    unreal.log(f"Gahyeon coarse MetaHuman POC saved: {TARGET_CHARACTER}")


conform_coarse_identity_v024()
