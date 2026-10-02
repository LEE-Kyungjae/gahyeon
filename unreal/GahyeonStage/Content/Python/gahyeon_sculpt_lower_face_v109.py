"""Create a conservative MetaHuman-native lower-face correction from measured v106 deltas."""

import json
from pathlib import Path

import unreal


SOURCE = "/Game/Gahyeon/CharacterPipeline/v087/Character/MHC_Skotukeda_WardrobeGroom_v087"
TARGET = "/Game/Gahyeon/CharacterPipeline/v109b/Character/MHC_Gahyeon_LowerFace_v109b"
RECEIPT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v109b-metahuman-lower-face-sculpt/sculpt-receipt.json"
)
INDICES = (11, 44, 66)
DELTAS_CM = (
    unreal.Vector(0.0, 0.0, 0.35),
    unreal.Vector(0.0, 0.0, 0.15),
    unreal.Vector(0.0, 0.0, 0.15),
)


def vector(value):
    return [value.x, value.y, value.z]


def sculpt_lower_face_v109():
    if RECEIPT.exists() or unreal.EditorAssetLibrary.does_asset_exist(TARGET):
        raise RuntimeError("refusing to overwrite immutable v109b sculpt")
    source = unreal.load_asset(SOURCE)
    if source is None or source.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError(f"source MetaHuman Character unavailable: {SOURCE}")
    character = unreal.EditorAssetLibrary.duplicate_asset(SOURCE, TARGET)
    if character is None or character.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError("failed to duplicate v087 MetaHuman Character")
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    if not subsystem.try_add_object_to_edit(character):
        raise RuntimeError("v109b MetaHuman Character could not be opened for sculpting")
    try:
        before = subsystem.get_face_landmarks(character)
        if len(before) != 77:
            raise RuntimeError(f"unexpected sculpt landmark count: {len(before)}")
        subsystem.translate_face_landmarks(character, list(INDICES), list(DELTAS_CM))
        after = subsystem.get_face_landmarks(character)
        if len(after) != len(before):
            raise RuntimeError("landmark count changed after topology-preserving sculpt")
        changes = []
        for index, requested in zip(INDICES, DELTAS_CM):
            actual = after[index] - before[index]
            if actual.z <= 0.0 or actual.z > requested.z + 0.001:
                raise RuntimeError(f"landmark {index} constrained delta is unsafe: {vector(actual)}")
            changes.append({
                "index": index,
                "before": vector(before[index]),
                "requestedDeltaCm": vector(requested),
                "deltaCm": vector(actual),
                "after": vector(after[index]),
            })
        if not unreal.EditorAssetLibrary.save_loaded_asset(character, only_if_is_dirty=False):
            raise RuntimeError("failed to save v109b MetaHuman Character")
    finally:
        if subsystem.is_object_added_for_editing(character):
            subsystem.remove_object_to_edit(character)
    RECEIPT.parent.mkdir(parents=True, exist_ok=False)
    RECEIPT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v109b",
        "state": "sculpted-awaiting-rig-and-fixed-camera-qa",
        "engine": "5.8",
        "hypothesis": "The v106 face is close in eye, nose and mouth width, but its lower face is about 10 percent too long against canonical 03.",
        "action": "Lift only the MetaHuman chin and bilateral lower-jaw landmarks by conservative sub-centimeter deltas.",
        "expectedResult": "Reduce mouth-to-chin and nose-tip-to-chin ratios without regressing eye spacing, eye width, mouth width or nose width.",
        "sourceCharacter": SOURCE,
        "character": character.get_path_name(),
        "changes": changes,
        "topologyModified": False,
        "cloudRigRequested": False,
        "automaticApproval": False,
        "productionReady": False,
    }, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v109b conservative lower-face sculpt saved: {TARGET}")
    unreal.SystemLibrary.quit_editor()


sculpt_lower_face_v109()
