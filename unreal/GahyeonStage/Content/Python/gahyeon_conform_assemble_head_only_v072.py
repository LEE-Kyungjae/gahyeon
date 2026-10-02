"""Conform the valid v071 Z-up Identity and assemble an immutable v072 Medium POC."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import unreal


SOURCE = "/Game/Fab/MetaHuman/Skotukeda"
IDENTITY = "/Game/Gahyeon/CharacterPipeline/v071/Identity/MHI_Gahyeon_HeadOnly_v071"
CHARACTER = "/Game/Gahyeon/CharacterPipeline/v072/Character/MHC_Gahyeon_HeadOnly_v072"
BUILD_ROOT = "/Game/Gahyeon/CharacterPipeline/v072/AssembledMedium"
COMMON_ROOT = "/Game/Gahyeon/CharacterPipeline/v072/CommonMedium"


def conform_assemble_head_only_v072():
    workspace = Path(os.environ.get("GAHYEON_WORKSPACE", "/Users/ze/work/gahyeonbot"))
    receipt = workspace / "artifacts/gahyeon-ch/metahuman-head-only-v072-assembly.json"
    if receipt.exists():
        raise RuntimeError(f"refusing to overwrite immutable receipt: {receipt}")
    if unreal.EditorAssetLibrary.does_asset_exist(CHARACTER):
        raise RuntimeError(f"refusing to overwrite v072 character: {CHARACTER}")
    for path in (BUILD_ROOT, COMMON_ROOT):
        if unreal.EditorAssetLibrary.list_assets(path, recursive=True, include_folder=False):
            raise RuntimeError(f"refusing to overwrite v072 assets: {path}")
    identity = unreal.EditorAssetLibrary.load_asset(IDENTITY)
    if identity is None or identity.get_class().get_name() != "MetaHumanIdentity":
        raise RuntimeError(f"v071 solved Identity is unavailable: {IDENTITY}")
    character = unreal.EditorAssetLibrary.duplicate_asset(SOURCE, CHARACTER)
    if character is None or character.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError(f"failed to duplicate source MetaHuman: {SOURCE}")
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    if not subsystem.try_add_object_to_edit(character):
        raise RuntimeError("v072 MetaHuman Character is unavailable for editing")
    try:
        params = unreal.ImportFromIdentityParams()
        params.use_eye_meshes = False
        params.use_teeth_mesh = False
        params.use_metric_scale = True
        result = subsystem.import_from_identity(character, identity, params)
        if result != unreal.ImportErrorCode.SUCCESS:
            raise RuntimeError(f"v072 import_from_identity failed: {result}")
        subsystem.commit_face_state(character)

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
            raise RuntimeError(f"failed to save enriched v072 character: {CHARACTER}")
        if not subsystem.can_build_meta_human(character, True):
            raise RuntimeError("v072 is not buildable after cloud enrichment")

        build = unreal.MetaHumanCharacterEditorBuildParameters()
        build.pipeline_type = unreal.MetaHumanDefaultPipelineType.OPTIMIZED
        build.pipeline_quality = unreal.MetaHumanQualityLevel.MEDIUM
        build.animation_system_name = "AnimBP"
        build.absolute_build_path = BUILD_ROOT
        build.common_folder_path = COMMON_ROOT
        build.name_override = "Gahyeon_HeadOnly_v072"
        subsystem.build_meta_human(character, build)
    finally:
        subsystem.remove_object_to_edit(character)

    assets = list(unreal.EditorAssetLibrary.list_assets(BUILD_ROOT, recursive=True, include_folder=False))
    if not assets:
        raise RuntimeError("v072 Medium assembly produced no assets")
    for path in (BUILD_ROOT, COMMON_ROOT):
        if not unreal.EditorAssetLibrary.save_directory(path, only_if_is_dirty=False, recursive=True):
            raise RuntimeError(f"failed to save v072 assembly directory: {path}")
    blueprints = [path for path in assets if path.rsplit("/", 1)[-1].startswith("BP_")]
    if len(blueprints) != 1:
        raise RuntimeError(f"expected exactly one v072 Blueprint, got: {blueprints}")
    value = {
        "schemaVersion": 1,
        "observedAt": datetime.now(timezone.utc).isoformat(),
        "iteration": "v072",
        "identityAsset": IDENTITY,
        "sourceCharacter": SOURCE,
        "characterAsset": CHARACTER,
        "assembledBlueprint": blueprints[0],
        "assembledAssetCount": len(assets),
        "assembledAssets": assets,
        "params": {"useEyeMeshes": False, "useTeethMesh": False, "useMetricScale": True},
        "pipelineType": "OPTIMIZED",
        "pipelineQuality": "MEDIUM",
        "hypothesis": "The Z-up head-only solve produces a structurally normal assembled MetaHuman with default eyes and teeth.",
        "status": "draft",
        "automaticApproval": False,
        "identityApproved": False,
        "productionReady": False,
        "aaaQualityClaim": False,
    }
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v072 head-only Medium assembly complete: {json.dumps(value)}")


conform_assemble_head_only_v072()
