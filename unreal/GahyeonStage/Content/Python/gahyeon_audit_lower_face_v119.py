"""Recover v119 evidence by comparing the saved native MetaHuman assets."""

import json
from pathlib import Path

import unreal


SOURCE = "/Game/Gahyeon/CharacterPipeline/v087/Character/MHC_Skotukeda_WardrobeGroom_v087"
TARGET = "/Game/Gahyeon/CharacterPipeline/v119/Character/MHC_Gahyeon_LowerFace_v119"
RECEIPT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v119-metahuman-lower-face-sculpt/sculpt-receipt.json"
)
INDICES = (11, 44, 66, 1, 27)
REQUESTED_Z_CM = (1.20, 0.70, 0.70, 0.35, 0.35)


def positions_v119(character, subsystem):
    if not subsystem.try_add_object_to_edit(character):
        raise RuntimeError(f"could not open character for audit: {character.get_path_name()}")
    try:
        values = subsystem.get_face_landmarks(character)
        if len(values) != 77:
            raise RuntimeError(f"unexpected landmark count: {len(values)}")
        return [[value.x, value.y, value.z] for value in values]
    finally:
        if subsystem.is_object_added_for_editing(character):
            subsystem.remove_object_to_edit(character)


def audit_lower_face_v119():
    if RECEIPT.exists():
        raise RuntimeError("refusing to overwrite immutable v119 receipt")
    source = unreal.load_asset(SOURCE)
    target = unreal.load_asset(TARGET)
    if source is None or target is None:
        raise RuntimeError("v087 source or saved v119 target is unavailable")
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    before = positions_v119(source, subsystem)
    after = positions_v119(target, subsystem)
    changes = []
    for index, requested_z in zip(INDICES, REQUESTED_Z_CM):
        delta = [after[index][axis] - before[index][axis] for axis in range(3)]
        if delta[2] <= 0.0 or delta[2] > requested_z + 0.001:
            raise RuntimeError(f"saved landmark {index} has unsafe Z delta: {delta}")
        if abs(delta[0]) > 0.25 or abs(delta[1]) > 0.25:
            raise RuntimeError(f"saved landmark {index} has excessive lateral/depth drift: {delta}")
        changes.append({
            "index": index,
            "before": before[index],
            "requestedDeltaCm": [0.0, 0.0, requested_z],
            "actualDeltaCm": delta,
            "after": after[index],
        })
    RECEIPT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v119",
        "state": "saved-native-sculpt-audited-awaiting-fixed-camera-qa",
        "engine": "5.8",
        "hypothesis": "The v113 face is measurably 6-11 percent too long below the eye/nose/mouth lines, while mouth and nose width are already within 0.5 percent of canonical 03.",
        "action": "Lift only five native MetaHuman chin and jaw landmarks from the clean v087 branch; do not change width, eyes, nose, mouth, topology, hair, materials, or clothing.",
        "expectedResult": "Reduce lower-face vertical ratios without reintroducing the direct-mesh distortions seen in rejected MPFB iterations.",
        "sourceCharacter": SOURCE,
        "character": TARGET,
        "landmarkSemanticMap": "../v118-metahuman-landmark-map/front-index-map.png",
        "recoveredAfterReceiptWriteFailure": True,
        "changes": changes,
        "topologyModified": False,
        "automaticApproval": False,
        "productionReady": False,
    }, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v119 saved sculpt audit written: {RECEIPT}")
    unreal.SystemLibrary.quit_editor()


audit_lower_face_v119()
