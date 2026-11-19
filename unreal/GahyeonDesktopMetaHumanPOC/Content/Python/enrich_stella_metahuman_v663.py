"""Request production facial rig and texture sources for Stella v661."""

import json
from pathlib import Path

import unreal


CHARACTER = "/Game/LivingCharacterPOC/v661/Character/MHC_StellaLily_Draft_v661"
CONFORM_RECEIPT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/"
    "living-character-poc-v661-stella-metahuman-conform/conform-receipt.json"
)
RECEIPT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/"
    "living-character-poc-v663-stella-metahuman-enrichment/enrichment-receipt.json"
)


def enrich_stella_metahuman_v663():
    if RECEIPT.exists():
        raise RuntimeError("refusing to overwrite immutable v663 receipt")
    conform = json.loads(CONFORM_RECEIPT.read_text(encoding="utf-8"))
    if conform.get("state") != "draft-conformed-awaiting-fixed-camera-surface-qa":
        raise RuntimeError("Stella v661 conform lineage is not ready")
    character = unreal.load_asset(CHARACTER)
    if character is None or character.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError(f"Stella v661 MetaHuman unavailable: {CHARACTER}")
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    if not subsystem.try_add_object_to_edit(character):
        raise RuntimeError("Stella v661 could not be opened for enrichment")
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
        if not subsystem.can_build_meta_human(character, True):
            raise RuntimeError("Stella enrichment returned but character is not buildable")
        if not unreal.EditorAssetLibrary.save_loaded_asset(
            character, only_if_is_dirty=False
        ):
            raise RuntimeError("failed to save enriched Stella character")
    finally:
        if subsystem.is_object_added_for_editing(character):
            subsystem.remove_object_to_edit(character)
    RECEIPT.parent.mkdir(parents=True, exist_ok=False)
    RECEIPT.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "iteration": "v663",
                "state": "enriched-buildable-awaiting-assembly",
                "engine": "5.8",
                "character": CHARACTER,
                "conformReceipt": str(CONFORM_RECEIPT),
                "rigType": "JOINTS_AND_BLEND_SHAPES",
                "textureSourcesRequested": True,
                "canBuildMetaHuman": True,
                "automaticApproval": False,
                "productionReady": False,
            },
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    unreal.log(f"Stella v663 enrichment complete: {CHARACTER}")
    unreal.SystemLibrary.quit_editor()


enrich_stella_metahuman_v663()
