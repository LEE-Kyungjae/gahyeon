"""Reload and record the saved v024 coarse MetaHuman POC without opening its heavy editor."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import unreal


IDENTITY_ASSET = "/Game/Gahyeon/CharacterPipeline/v024/Identity/MHI_Gahyeon_v024"
TARGET_CHARACTER = "/Game/Gahyeon/CharacterPipeline/v024/Character/MHC_Gahyeon_CoarsePOC_v024"


def validate_coarse_poc_v024():
    workspace = Path(os.environ.get("GAHYEON_WORKSPACE", "/Users/ze/work/gahyeonbot"))
    identity = unreal.EditorAssetLibrary.load_asset(IDENTITY_ASSET)
    character = unreal.EditorAssetLibrary.load_asset(TARGET_CHARACTER)
    if identity is None or character is None:
        raise RuntimeError("v024 Identity or MetaHuman Character did not survive a clean reload")

    identity_file = workspace / "unreal/GahyeonStage/Content/Gahyeon/CharacterPipeline/v024/Identity/MHI_Gahyeon_v024.uasset"
    skeletal_file = workspace / "unreal/GahyeonStage/Content/Gahyeon/CharacterPipeline/v024/Identity/SK_MHI_Gahyeon_v024.uasset"
    dna_file = workspace / "unreal/GahyeonStage/Content/Gahyeon/CharacterPipeline/v024/Identity/SK_MHI_Gahyeon_v024_DNA.uasset"
    character_file = workspace / "unreal/GahyeonStage/Content/Gahyeon/CharacterPipeline/v024/Character/MHC_Gahyeon_CoarsePOC_v024.uasset"
    required_files = (identity_file, skeletal_file, dna_file, character_file)
    if not all(path.is_file() for path in required_files):
        raise RuntimeError("one or more v024 reload dependencies are missing on disk")

    receipt_path = workspace / "artifacts/gahyeon-ch/metahuman-coarse-poc-v024.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "observedAt": datetime.now(timezone.utc).isoformat(),
                "iteration": "v024",
                "engine": "Unreal Engine 5.8",
                "identityAsset": IDENTITY_ASSET,
                "targetCharacter": TARGET_CHARACTER,
                "cleanReloadVerified": True,
                "identityFileExists": True,
                "skeletalMeshFileExists": True,
                "dnaFileExists": True,
                "characterFileExists": True,
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
    unreal.log(f"Gahyeon coarse MetaHuman POC clean reload verified: {TARGET_CHARACTER}")


validate_coarse_poc_v024()
