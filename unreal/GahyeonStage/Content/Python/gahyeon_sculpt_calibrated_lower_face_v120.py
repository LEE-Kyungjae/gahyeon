"""Create a calibrated native MetaHuman lower-face experiment from v119 response."""

import json
from pathlib import Path

import unreal


SOURCE = "/Game/Gahyeon/CharacterPipeline/v087/Character/MHC_Skotukeda_WardrobeGroom_v087"
TARGET = "/Game/Gahyeon/CharacterPipeline/v120/Character/MHC_Gahyeon_LowerFace_v120"
CALIBRATION = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v119-metahuman-lower-face-sculpt/sculpt-receipt.json"
)
RECEIPT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v120-metahuman-lower-face-calibrated/sculpt-receipt.json"
)
REQUESTS = {
    11: unreal.Vector(0.0, 0.0, 3.00),
    44: unreal.Vector(0.0, 0.0, 3.00),
    66: unreal.Vector(0.0, 0.0, 3.00),
    1: unreal.Vector(0.0, 0.0, 1.20),
    27: unreal.Vector(0.0, 0.0, 1.20),
}


def vector_v120(value):
    return [value.x, value.y, value.z]


def sculpt_calibrated_lower_face_v120():
    if RECEIPT.exists() or unreal.EditorAssetLibrary.does_asset_exist(TARGET):
        raise RuntimeError("refusing to overwrite immutable v120 output")
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    if calibration.get("state") != "saved-native-sculpt-audited-awaiting-fixed-camera-qa":
        raise RuntimeError("v119 measured-response calibration is unavailable")
    source = unreal.load_asset(SOURCE)
    if source is None or source.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError(f"source MetaHuman Character unavailable: {SOURCE}")
    character = unreal.EditorAssetLibrary.duplicate_asset(SOURCE, TARGET)
    if character is None or character.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError("failed to duplicate v087 MetaHuman Character")
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    if not subsystem.try_add_object_to_edit(character):
        unreal.EditorAssetLibrary.delete_asset(TARGET)
        raise RuntimeError("v120 MetaHuman Character could not be opened for sculpting")
    succeeded = False
    try:
        before = subsystem.get_face_landmarks(character)
        indices = list(REQUESTS)
        requested = [REQUESTS[index] for index in indices]
        subsystem.translate_face_landmarks(character, indices, requested)
        subsystem.commit_face_state(character)
        after = subsystem.get_face_landmarks(character)
        changes = []
        for index, request in zip(indices, requested):
            actual = after[index] - before[index]
            if actual.z <= 0.0 or actual.z > 1.20:
                raise RuntimeError(f"landmark {index} exceeds safe vertical envelope: {vector_v120(actual)}")
            if abs(actual.x) > 0.50 or abs(actual.y) > 0.50:
                raise RuntimeError(f"landmark {index} exceeds lateral/depth envelope: {vector_v120(actual)}")
            changes.append({
                "index": index,
                "before": vector_v120(before[index]),
                "requestedDeltaCm": vector_v120(request),
                "actualDeltaCm": vector_v120(actual),
                "after": vector_v120(after[index]),
            })
        if not unreal.EditorAssetLibrary.save_loaded_asset(character, only_if_is_dirty=False):
            raise RuntimeError("failed to save v120 MetaHuman Character")
        succeeded = True
    finally:
        if subsystem.is_object_added_for_editing(character):
            subsystem.remove_object_to_edit(character)
        if not succeeded:
            unreal.EditorAssetLibrary.delete_asset(TARGET)
    RECEIPT.parent.mkdir(parents=True, exist_ok=False)
    RECEIPT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v120",
        "state": "saved-calibrated-native-sculpt-awaiting-fixed-camera-qa",
        "engine": "5.8",
        "hypothesis": "v119 proved the MetaHuman PCA accepts only 9-22 percent of the requested lower-face translation; a calibrated request should produce a visible but topology-safe correction.",
        "action": "Apply one calibrated native landmark request from v087 and reject before saving if actual vertical or lateral/depth movement exceeds the fixed safety envelope.",
        "expectedResult": "Move the chin and jaw enough to test the measured 6-11 percent lower-face error without direct vertex editing.",
        "sourceCharacter": SOURCE,
        "character": TARGET,
        "calibrationReceipt": str(CALIBRATION),
        "changes": changes,
        "safetyEnvelopeCm": {"maximumVertical": 1.20, "maximumLateralOrDepth": 0.50},
        "topologyModified": False,
        "automaticApproval": False,
        "productionReady": False,
    }, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v120 calibrated lower-face sculpt saved: {TARGET}")
    unreal.SystemLibrary.quit_editor()


sculpt_calibrated_lower_face_v120()
