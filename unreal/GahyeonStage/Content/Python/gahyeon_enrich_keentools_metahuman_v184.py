"""Request production rig and textures for conformed KeenTools v183."""

import json
from pathlib import Path

import unreal


CHARACTER = "/Game/Gahyeon/CharacterPipeline/v183/Character/MHC_Gahyeon_KeenTools_v183"
CONFORM_RECEIPT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v183-ue58-keentools-metahuman-conform/conform-receipt.json"
)
RECEIPT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v184-metahuman-keentools-cloud/enrichment-receipt.json"
)


def enrich_keentools_metahuman_v184():
    if RECEIPT.exists():
        raise RuntimeError("refusing to overwrite immutable v184 receipt")
    conform = json.loads(CONFORM_RECEIPT.read_text(encoding="utf-8"))
    if conform.get("state") != "metahuman-conformed-awaiting-fixed-camera-identity-review":
        raise RuntimeError("v183 KeenTools conform lineage is not ready")
    character = unreal.load_asset(CHARACTER)
    if character is None or character.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError(f"v183 MetaHuman Character unavailable: {CHARACTER}")
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    if not subsystem.try_add_object_to_edit(character):
        raise RuntimeError("v183 could not be opened for cloud enrichment")
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
            raise RuntimeError("v183 cloud requests returned but character is not buildable")
        if not unreal.EditorAssetLibrary.save_loaded_asset(character, only_if_is_dirty=False):
            raise RuntimeError("failed to save cloud-enriched v183 character")
    finally:
        if subsystem.is_object_added_for_editing(character):
            subsystem.remove_object_to_edit(character)
    RECEIPT.parent.mkdir(parents=True, exist_ok=False)
    RECEIPT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v184",
        "state": "cloud-enriched-buildable-awaiting-assembly",
        "engine": "5.8",
        "character": character.get_path_name(),
        "conformReceipt": str(CONFORM_RECEIPT),
        "rigType": "JOINTS_AND_BLEND_SHAPES",
        "textureSourcesRequested": True,
        "canBuildMetaHuman": True,
        "automaticApproval": False,
        "productionReady": False,
    }, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v184 cloud enrichment complete: {CHARACTER}")
    unreal.SystemLibrary.quit_editor()


enrich_keentools_metahuman_v184()
