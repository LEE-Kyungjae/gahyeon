"""Request production MetaHuman rig and texture sources for calibrated v120."""

import json
from pathlib import Path

import unreal


CHARACTER = "/Game/Gahyeon/CharacterPipeline/v120/Character/MHC_Gahyeon_LowerFace_v120"
SCULPT_RECEIPT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v120-metahuman-lower-face-calibrated/sculpt-receipt.json"
)
RECEIPT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v121-metahuman-lower-face-cloud/enrichment-receipt.json"
)


def enrich_lower_face_v121():
    if RECEIPT.exists():
        raise RuntimeError(f"refusing to overwrite immutable v121 receipt: {RECEIPT}")
    sculpt = json.loads(SCULPT_RECEIPT.read_text(encoding="utf-8"))
    if sculpt.get("state") != "saved-calibrated-native-sculpt-awaiting-fixed-camera-qa":
        raise RuntimeError("v120 sculpt lineage is not ready for cloud enrichment")
    character = unreal.load_asset(CHARACTER)
    if character is None or character.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError(f"v120 MetaHuman Character unavailable: {CHARACTER}")
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    if not subsystem.try_add_object_to_edit(character):
        raise RuntimeError("v120 could not be opened for cloud enrichment")
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
            raise RuntimeError("v120 cloud requests returned but character is not buildable")
        if not unreal.EditorAssetLibrary.save_loaded_asset(character, only_if_is_dirty=False):
            raise RuntimeError("failed to save cloud-enriched v120 character")
    finally:
        if subsystem.is_object_added_for_editing(character):
            subsystem.remove_object_to_edit(character)
    RECEIPT.parent.mkdir(parents=True, exist_ok=False)
    RECEIPT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v121",
        "state": "cloud-enriched-buildable-awaiting-assembly",
        "engine": "5.8",
        "character": character.get_path_name(),
        "sculptReceipt": str(SCULPT_RECEIPT),
        "rigType": "JOINTS_AND_BLEND_SHAPES",
        "textureSourcesRequested": True,
        "canBuildMetaHuman": True,
        "automaticApproval": False,
        "productionReady": False,
    }, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v121 MetaHuman cloud enrichment complete: {CHARACTER}")
    unreal.SystemLibrary.quit_editor()


enrich_lower_face_v121()
