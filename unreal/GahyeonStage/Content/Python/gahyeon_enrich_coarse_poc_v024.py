"""Request blocking MetaHuman POC texture and rig assets without opening the Character editor."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import unreal


SOURCE_CHARACTER_PATH = "/Game/Fab/MetaHuman/Skotukeda"
CHARACTER_PATH = "/Game/Gahyeon/CharacterPipeline/v026/Character/MHC_Skotukeda_Baseline_v026"


def enrich():
    workspace = Path(os.environ.get("GAHYEON_WORKSPACE", "/Users/ze/work/gahyeonbot"))
    receipt_path = workspace / "artifacts/gahyeon-ch/metahuman-template-baseline-v026-enrichment.json"
    if receipt_path.exists():
        raise RuntimeError(f"refusing to overwrite immutable enrichment receipt: {receipt_path}")

    if unreal.EditorAssetLibrary.does_asset_exist(CHARACTER_PATH):
        raise RuntimeError(f"refusing to overwrite existing template baseline: {CHARACTER_PATH}")
    character = unreal.EditorAssetLibrary.duplicate_asset(
        SOURCE_CHARACTER_PATH, CHARACTER_PATH
    )
    if character is None:
        raise RuntimeError(f"MetaHuman Character is unavailable: {CHARACTER_PATH}")
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    if not subsystem.try_add_object_to_edit(character):
        raise RuntimeError("failed to initialize MetaHuman Character for enrichment")
    try:
        rig = unreal.MetaHumanCharacterAutoRiggingRequestParams()
        rig.blocking = True
        rig.report_progress = False
        rig.rig_type = unreal.MetaHumanRigType.JOINTS_AND_BLEND_SHAPES
        subsystem.request_auto_rigging(character, rig)

        textures = unreal.MetaHumanCharacterTextureRequestParams()
        textures.blocking = True
        textures.report_progress = False
        subsystem.request_texture_sources(character, textures)

        if not unreal.EditorAssetLibrary.save_loaded_asset(character, only_if_is_dirty=False):
            raise RuntimeError(f"failed to save enriched MetaHuman Character: {CHARACTER_PATH}")
        can_build = subsystem.can_build_meta_human(character, True)
    finally:
        subsystem.remove_object_to_edit(character)

    if not can_build:
        raise RuntimeError("texture and rig requests returned, but MetaHuman still cannot be assembled")

    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "observedAt": datetime.now(timezone.utc).isoformat(),
                "iteration": "v026",
                "engine": "Unreal Engine 5.8",
                "characterAsset": CHARACTER_PATH,
                "textureSourcesRequested": True,
                "autoRigRequested": True,
                "rigType": "JOINTS_AND_BLENDSHAPES",
                "canAssemble": True,
                "qualityStage": "unaltered-template-baseline-poc",
                "automaticApproval": False,
                "productionReady": False,
                "aaaQualityClaim": False,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    unreal.log(f"Gahyeon v026 template baseline enrichment complete: {CHARACTER_PATH}")


enrich()
