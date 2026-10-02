"""Apply the bounded v129 PCA proposal to a new native MetaHuman Character."""

import json
from pathlib import Path

import unreal


SOURCE = "/Game/Gahyeon/CharacterPipeline/v087/Character/MHC_Skotukeda_WardrobeGroom_v087"
TARGET = "/Game/Gahyeon/CharacterPipeline/v130/Character/MHC_Gahyeon_JointIdentity_v130"
PROPOSAL = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v129-metahuman-joint-identity-solve/coefficient-proposal.json"
)
RECEIPT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v130-metahuman-joint-identity-native/application-receipt.json"
)


def apply_joint_identity_solve_v130():
    if RECEIPT.exists() or unreal.EditorAssetLibrary.does_asset_exist(TARGET):
        raise RuntimeError("refusing to overwrite immutable v130 output")
    proposal = json.loads(PROPOSAL.read_text(encoding="utf-8"))
    if proposal.get("state") != "bounded-pca-proposal-awaiting-native-application":
        raise RuntimeError("v129 bounded PCA proposal is unavailable")
    source = unreal.load_asset(SOURCE)
    if source is None or source.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError(f"source MetaHuman Character unavailable: {SOURCE}")
    character = unreal.EditorAssetLibrary.duplicate_asset(SOURCE, TARGET)
    if character is None or character.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError("failed to duplicate clean v087 MetaHuman Character")
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    if not subsystem.try_add_object_to_edit(character):
        unreal.EditorAssetLibrary.delete_asset(TARGET)
        raise RuntimeError("could not open v130 for native PCA application")
    succeeded = False
    try:
        coefficients = list(subsystem.get_face_model_coefficients(character))
        before = list(subsystem.get_face_landmarks(character))
        for change in proposal["coefficientChanges"]:
            index = change["coefficientIndex"]
            if abs(coefficients[index] - change["baseValue"]) > 0.0001:
                raise RuntimeError(f"coefficient baseline drift at index {index}")
            coefficients[index] = change["resultValue"]
        subsystem.set_face_model_coefficients(character, coefficients)
        after = list(subsystem.get_face_landmarks(character))
        measured = []
        maximum_delta = 0.0
        for index, (start, end) in enumerate(zip(before, after)):
            delta = [end.x - start.x, end.y - start.y, end.z - start.z]
            magnitude = sum(value * value for value in delta) ** 0.5
            maximum_delta = max(maximum_delta, magnitude)
            measured.append({"landmarkIndex": index, "deltaCm": delta, "magnitudeCm": magnitude})
        if maximum_delta > 1.25:
            raise RuntimeError(f"joint identity solve exceeded safe landmark envelope: {maximum_delta} cm")
        subsystem.commit_face_state(character)
        if not unreal.EditorAssetLibrary.save_loaded_asset(character, only_if_is_dirty=False):
            raise RuntimeError("failed to save v130 MetaHuman Character")
        succeeded = True
    finally:
        if subsystem.is_object_added_for_editing(character):
            subsystem.remove_object_to_edit(character)
        if not succeeded:
            unreal.EditorAssetLibrary.delete_asset(TARGET)
    RECEIPT.parent.mkdir(parents=True, exist_ok=False)
    RECEIPT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v130",
        "state": "saved-native-joint-identity-awaiting-fixed-camera-qa",
        "engine": "5.8",
        "sourceCharacter": SOURCE,
        "character": TARGET,
        "proposal": str(PROPOSAL),
        "changedCoefficientCount": len(proposal["coefficientChanges"]),
        "maximumLandmarkDeltaCm": maximum_delta,
        "measuredLandmarkDeltas": measured,
        "topologyModified": False,
        "automaticApproval": False,
        "productionReady": False,
    }, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v130 native joint identity saved: {TARGET}")
    unreal.SystemLibrary.quit_editor()


apply_joint_identity_solve_v130()
