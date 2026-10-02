"""Measure native MetaHuman PCA coefficient influence without saving an asset."""

import json
import time
from pathlib import Path

import unreal


SOURCE = "/Game/Gahyeon/CharacterPipeline/v087/Character/MHC_Skotukeda_WardrobeGroom_v087"
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v127-metahuman-pca-sensitivity/probe-report.json"
)
SAMPLE_LIMIT = 32
EPSILON = 0.50


def vector_v127(value):
    return [value.x, value.y, value.z]


def probe_face_coefficient_sensitivity_v127():
    if REPORT.exists():
        raise RuntimeError("refusing to overwrite immutable v127 report")
    character = unreal.load_asset(SOURCE)
    if character is None or character.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError(f"source MetaHuman Character unavailable: {SOURCE}")
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    if not subsystem.try_add_object_to_edit(character):
        raise RuntimeError("could not open v087 for read-only PCA probing")
    restored = False
    started = time.perf_counter()
    try:
        base_coefficients = list(subsystem.get_face_model_coefficients(character))
        base_landmarks = list(subsystem.get_face_landmarks(character))
        if len(base_landmarks) != 77 or len(base_coefficients) < 11:
            raise RuntimeError(
                f"unexpected face state: coefficients={len(base_coefficients)}, "
                f"landmarks={len(base_landmarks)}"
            )
        first_patch_count = int(base_coefficients[9])
        if first_patch_count <= 0 or 10 + first_patch_count > len(base_coefficients):
            raise RuntimeError(f"invalid first PCA patch size: {first_patch_count}")
        sample_count = min(SAMPLE_LIMIT, first_patch_count)
        samples = []
        for offset in range(sample_count):
            coefficient_index = 10 + offset
            trial = list(base_coefficients)
            trial[coefficient_index] += EPSILON
            subsystem.set_face_model_coefficients(character, trial)
            landmarks = list(subsystem.get_face_landmarks(character))
            deltas = []
            maximum_delta = 0.0
            for landmark_index, (before, after) in enumerate(zip(base_landmarks, landmarks)):
                delta = after - before
                magnitude = (delta.x * delta.x + delta.y * delta.y + delta.z * delta.z) ** 0.5
                maximum_delta = max(maximum_delta, magnitude)
                if magnitude >= 0.0001:
                    deltas.append({
                        "landmarkIndex": landmark_index,
                        "deltaCm": vector_v127(delta),
                        "magnitudeCm": magnitude,
                    })
            samples.append({
                "coefficientIndex": coefficient_index,
                "baseValue": base_coefficients[coefficient_index],
                "epsilon": EPSILON,
                "maximumLandmarkDeltaCm": maximum_delta,
                "affectedLandmarkCount": len(deltas),
                "landmarkDeltas": deltas,
            })
        subsystem.set_face_model_coefficients(character, base_coefficients)
        restored_landmarks = list(subsystem.get_face_landmarks(character))
        restoration_error = max((
            ((after.x - before.x) ** 2
             + (after.y - before.y) ** 2
             + (after.z - before.z) ** 2) ** 0.5
            for before, after in zip(base_landmarks, restored_landmarks)
        ), default=0.0)
        restored = restoration_error < 0.0001
        if not restored:
            raise RuntimeError(f"PCA state restoration error: {restoration_error} cm")
        REPORT.parent.mkdir(parents=True, exist_ok=False)
        REPORT.write_text(json.dumps({
            "schemaVersion": 1,
            "iteration": "v127",
            "state": "read-only-pca-sensitivity-sample",
            "engine": "5.8",
            "sourceCharacter": SOURCE,
            "coefficientCount": len(base_coefficients),
            "coefficientHeader": base_coefficients[:10],
            "firstPatchCoefficientCount": first_patch_count,
            "sampleCount": sample_count,
            "epsilon": EPSILON,
            "elapsedSeconds": time.perf_counter() - started,
            "stateRestored": restored,
            "maximumRestorationErrorCm": restoration_error,
            "assetSaved": False,
            "samples": samples,
        }, indent=2) + "\n", encoding="utf-8")
    finally:
        if not restored:
            try:
                subsystem.set_face_model_coefficients(character, base_coefficients)
            except Exception as error:
                unreal.log_error(f"failed to restore PCA state: {error}")
        if subsystem.is_object_added_for_editing(character):
            subsystem.remove_object_to_edit(character)
    unreal.log(f"Gahyeon v127 PCA sensitivity report written: {REPORT}")
    unreal.SystemLibrary.quit_editor()


probe_face_coefficient_sensitivity_v127()
