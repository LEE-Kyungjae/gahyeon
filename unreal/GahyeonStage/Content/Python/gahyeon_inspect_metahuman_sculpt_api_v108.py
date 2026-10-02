"""Read the UE 5.8 MetaHuman sculpt state without modifying the source character."""

import json
from pathlib import Path

import unreal


CHARACTER = "/Game/Gahyeon/CharacterPipeline/v087/Character/MHC_Skotukeda_WardrobeGroom_v087"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v108-metahuman-sculpt-probe/sculpt-state.json"
)


def vector(value):
    return [value.x, value.y, value.z]


def inspect_metahuman_sculpt_api():
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to overwrite immutable v108 probe: {OUTPUT}")
    character = unreal.load_asset(CHARACTER)
    if character is None or character.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError(f"MetaHuman Character unavailable: {CHARACTER}")
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    if not subsystem.try_add_object_to_edit(character):
        raise RuntimeError("MetaHuman Character could not be opened for read-only inspection")
    try:
        landmarks = subsystem.get_face_landmarks(character)
        coefficients = subsystem.get_face_model_coefficients(character)
        if not landmarks:
            raise RuntimeError("MetaHuman sculpt landmarks are empty")
        values = [vector(item) for item in landmarks]
        axes = list(zip(*values))
        axis_ranges = {
            name: {"min": min(axis), "max": max(axis), "span": max(axis) - min(axis)}
            for name, axis in zip(("x", "y", "z"), axes)
        }
        lowest_z = sorted(enumerate(values), key=lambda item: item[1][2])[:8]
        OUTPUT.parent.mkdir(parents=True, exist_ok=False)
        OUTPUT.write_text(json.dumps({
            "schemaVersion": 1,
            "iteration": "v108",
            "state": "read-only-metahuman-sculpt-probe",
            "engine": "5.8",
            "character": character.get_path_name(),
            "landmarkCount": len(values),
            "coefficientCount": len(coefficients),
            "axisRanges": axis_ranges,
            "landmarks": [{"index": index, "position": position} for index, position in enumerate(values)],
            "lowestZCandidates": [{"index": index, "position": position} for index, position in lowest_z],
            "automaticApproval": False,
            "productionReady": False,
        }, indent=2) + "\n", encoding="utf-8")
    finally:
        subsystem.remove_object_to_edit(character)
    unreal.log(f"Gahyeon v108 MetaHuman sculpt probe written: {OUTPUT}")
    unreal.SystemLibrary.quit_editor()


inspect_metahuman_sculpt_api()
