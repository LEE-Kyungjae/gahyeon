"""Create an immutable MetaHuman-native lower-face proportion experiment."""

import json
from pathlib import Path

import unreal


SOURCE = "/Game/Gahyeon/CharacterPipeline/v087/Character/MHC_Skotukeda_WardrobeGroom_v087"
TARGET = "/Game/Gahyeon/CharacterPipeline/v119/Character/MHC_Gahyeon_LowerFace_v119"
RECEIPT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v119-metahuman-lower-face-sculpt/sculpt-receipt.json"
)
# Native sculpt landmarks identified from the immutable v108 X/Z semantic map.
# Each requested delta is intentionally below 1.25 cm and is applied once from v087.
REQUESTS = {
    11: unreal.Vector(0.0, 0.0, 1.20),  # chin tip
    44: unreal.Vector(0.0, 0.0, 0.70),  # lower jaw right
    66: unreal.Vector(0.0, 0.0, 0.70),  # lower jaw left
    1: unreal.Vector(0.0, 0.0, 0.35),   # mid jaw left
    27: unreal.Vector(0.0, 0.0, 0.35),  # mid jaw right
}


def vector_v119(value):
    return [value.x, value.y, value.z]


def sculpt_lower_face_v119():
    if RECEIPT.exists() or unreal.EditorAssetLibrary.does_asset_exist(TARGET):
        raise RuntimeError("refusing to overwrite immutable v119 sculpt")
    source = unreal.load_asset(SOURCE)
    if source is None or source.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError(f"source MetaHuman Character unavailable: {SOURCE}")
    character = unreal.EditorAssetLibrary.duplicate_asset(SOURCE, TARGET)
    if character is None or character.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError("failed to duplicate v087 MetaHuman Character")
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    if not subsystem.try_add_object_to_edit(character):
        unreal.EditorAssetLibrary.delete_asset(TARGET)
        raise RuntimeError("v119 MetaHuman Character could not be opened for sculpting")
    succeeded = False
    try:
        before = subsystem.get_face_landmarks(character)
        if len(before) != 77:
            raise RuntimeError(f"unexpected sculpt landmark count: {len(before)}")
        indices = list(REQUESTS)
        requested = [REQUESTS[index] for index in indices]
        subsystem.translate_face_landmarks(character, indices, requested)
        subsystem.commit_face_state(character)
        after = subsystem.get_face_landmarks(character)
        changes = []
        for index, request in zip(indices, requested):
            actual = after[index] - before[index]
            if actual.z <= 0.0 or actual.z > request.z + 0.001:
                raise RuntimeError(f"landmark {index} constrained delta is unsafe: {vector_v119(actual)}")
            if abs(actual.x) > 0.25 or abs(actual.y) > 0.25:
                raise RuntimeError(f"landmark {index} produced excessive lateral/depth drift: {vector_v119(actual)}")
            changes.append({
                "index": index,
                "before": vector_v119(before[index]),
                "requestedDeltaCm": vector_v119(request),
                "actualDeltaCm": vector_v119(actual),
                "after": vector_v119(after[index]),
            })
        if not unreal.EditorAssetLibrary.save_loaded_asset(character, only_if_is_dirty=False):
            raise RuntimeError("failed to save v119 MetaHuman Character")
        succeeded = True
    finally:
        if subsystem.is_object_added_for_editing(character):
            subsystem.remove_object_to_edit(character)
        if not succeeded:
            unreal.EditorAssetLibrary.delete_asset(TARGET)
    RECEIPT.parent.mkdir(parents=True, exist_ok=False)
    RECEIPT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v119",
        "state": "sculpted-awaiting-fixed-camera-qa",
        "engine": "5.8",
        "hypothesis": "The v113 face is measurably 6-11 percent too long below the eye/nose/mouth lines, while mouth and nose width are already within 0.5 percent of canonical 03.",
        "action": "Lift only five native MetaHuman chin and jaw landmarks from the clean v087 branch; do not change width, eyes, nose, mouth, topology, hair, materials, or clothing.",
        "expectedResult": "Reduce lower-face vertical ratios without reintroducing the direct-mesh distortions seen in rejected MPFB iterations.",
        "sourceCharacter": SOURCE,
        "character": character.get_path_name(),
        "landmarkSemanticMap": "../v118-metahuman-landmark-map/front-index-map.png",
        "changes": changes,
        "topologyModified": False,
        "automaticApproval": False,
        "productionReady": False,
    }, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v119 native lower-face sculpt saved: {TARGET}")
    unreal.SystemLibrary.quit_editor()


sculpt_lower_face_v119()
