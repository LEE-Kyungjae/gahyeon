"""Request the production MetaHuman face rig and texture sources for v109b."""

import json
from pathlib import Path

import unreal


CHARACTER = "/Game/Gahyeon/CharacterPipeline/v109b/Character/MHC_Gahyeon_LowerFace_v109b"
SCULPT_RECEIPT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v109b-metahuman-lower-face-sculpt/sculpt-receipt.json"
)
RECEIPT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v110b-metahuman-lower-face-cloud/enrichment-receipt.json"
)


def enrich_lower_face_v110():
    if RECEIPT.exists():
        raise RuntimeError(f"refusing to overwrite immutable v110b receipt: {RECEIPT}")
    if not SCULPT_RECEIPT.is_file():
        raise RuntimeError(f"v109b sculpt receipt unavailable: {SCULPT_RECEIPT}")
    sculpt = json.loads(SCULPT_RECEIPT.read_text(encoding="utf-8"))
    if sculpt.get("state") != "sculpted-awaiting-rig-and-fixed-camera-qa":
        raise RuntimeError("v109b sculpt lineage is not ready for cloud enrichment")
    character = unreal.load_asset(CHARACTER)
    if character is None or character.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError(f"v109b MetaHuman Character unavailable: {CHARACTER}")
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    if not subsystem.try_add_object_to_edit(character):
        raise RuntimeError("v109b could not be opened for cloud enrichment")
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
            raise RuntimeError("v109b cloud requests returned but character is not buildable")
        if not unreal.EditorAssetLibrary.save_loaded_asset(character, only_if_is_dirty=False):
            raise RuntimeError("failed to save cloud-enriched v109b character")
    finally:
        if subsystem.is_object_added_for_editing(character):
            subsystem.remove_object_to_edit(character)
    RECEIPT.parent.mkdir(parents=True, exist_ok=False)
    RECEIPT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v110b",
        "state": "cloud-enriched-buildable-awaiting-assembly",
        "engine": "5.8",
        "character": character.get_path_name(),
        "sculptReceipt": str(SCULPT_RECEIPT),
        "rigType": "JOINTS_AND_BLENDSHAPES",
        "textureSourcesRequested": True,
        "canBuildMetaHuman": True,
        "automaticApproval": False,
        "productionReady": False,
    }, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v110b MetaHuman cloud enrichment complete: {CHARACTER}")
    unreal.SystemLibrary.quit_editor()


enrich_lower_face_v110()
