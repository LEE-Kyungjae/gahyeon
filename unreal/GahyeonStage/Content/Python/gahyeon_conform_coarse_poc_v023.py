"""Create a non-approved coarse MetaHuman Character POC from solved Identity v023."""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import unreal


SOURCE_CHARACTER = "/Game/Fab/MetaHuman/Skotukeda"
IDENTITY_ASSET = "/Game/Gahyeon/CharacterPipeline/v023/Identity/MHI_Gahyeon_v023"
TARGET_CHARACTER = "/Game/Gahyeon/CharacterPipeline/v023/Character/MHC_Gahyeon_CoarsePOC_v023"


def conform_coarse_identity_v023():
    workspace = Path(os.environ["GAHYEON_WORKSPACE"]).resolve()
    receipt_path = workspace / "artifacts/gahyeon-ch/metahuman-coarse-poc-v023.json"
    if receipt_path.exists():
        raise RuntimeError(f"refusing to overwrite immutable receipt: {receipt_path}")
    if unreal.EditorAssetLibrary.does_asset_exist(TARGET_CHARACTER):
        raise RuntimeError(f"refusing to overwrite existing target: {TARGET_CHARACTER}")

    identity = unreal.EditorAssetLibrary.load_asset(IDENTITY_ASSET)
    source = unreal.EditorAssetLibrary.load_asset(SOURCE_CHARACTER)
    if identity is None or identity.get_class().get_name() != "MetaHumanIdentity":
        raise RuntimeError(f"conformed Identity missing: {IDENTITY_ASSET}")
    if source is None or source.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError(f"source MetaHuman Character missing: {SOURCE_CHARACTER}")

    character = unreal.EditorAssetLibrary.duplicate_asset(SOURCE_CHARACTER, TARGET_CHARACTER)
    if character is None or character.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError(f"failed to duplicate source character: {SOURCE_CHARACTER}")

    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    if not subsystem.try_add_object_to_edit(character):
        raise RuntimeError("coarse POC character is unavailable for editing")
    try:
        params = unreal.ImportFromIdentityParams()
        params.use_eye_meshes = True
        params.use_teeth_mesh = True
        params.use_metric_scale = True
        result = subsystem.import_from_identity(character, identity, params)
        if result != unreal.ImportErrorCode.SUCCESS:
            raise RuntimeError(f"import_from_identity failed: {result}")
        subsystem.commit_face_state(character)
        if not unreal.EditorAssetLibrary.save_loaded_asset(character, only_if_is_dirty=False):
            raise RuntimeError(f"failed to save coarse POC character: {TARGET_CHARACTER}")
    finally:
        subsystem.remove_object_to_edit(character)

    identity_file = workspace / "unreal/GahyeonStage/Content/Gahyeon/CharacterPipeline/v023/Identity/MHI_Gahyeon_v023.uasset"
    receipt = {
        "schemaVersion": 1,
        "observedAt": datetime.now(timezone.utc).isoformat(),
        "state": "coarse-head-conformed-awaiting-human-marker-review",
        "engine": "5.8",
        "sourceCharacter": SOURCE_CHARACTER,
        "identityAsset": IDENTITY_ASSET,
        "identitySha256": hashlib.sha256(identity_file.read_bytes()).hexdigest(),
        "characterAsset": TARGET_CHARACTER,
        "result": "SUCCESS",
        "headConformed": True,
        "markerAuthority": "default-neutral-contours-not-human-corrected",
        "automaticApproval": False,
        "identityApproved": False,
        "productionReady": False,
        "aaaQualityClaim": False,
        "nextAction": "render fixed desktop views and compare against canonical 03/06/07/08",
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).open_editor_for_assets([character])
    unreal.log(f"Gahyeon coarse MetaHuman POC conformed: {json.dumps(receipt)}")


conform_coarse_identity_v023()
