"""Build a sparse sensitivity matrix for every native MetaHuman PCA coefficient."""

import json
import time
from pathlib import Path

import unreal


SOURCE = "/Game/Gahyeon/CharacterPipeline/v087/Character/MHC_Skotukeda_WardrobeGroom_v087"
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v128-metahuman-pca-sensitivity-matrix/sensitivity-matrix.json"
)
EPSILON = 0.50


def parse_patch_layout_v128(coefficients):
    patch_count = int(coefficients[0])
    cursor = 1
    patches = []
    coefficient_indices = []
    for patch_index in range(patch_count):
        header_start = cursor
        coefficient_count = int(coefficients[cursor + 8])
        coefficient_start = cursor + 9
        coefficient_end = coefficient_start + coefficient_count
        if coefficient_count <= 0 or coefficient_end > len(coefficients):
            raise RuntimeError(
                f"invalid PCA patch {patch_index}: count={coefficient_count}, cursor={cursor}"
            )
        indices = list(range(coefficient_start, coefficient_end))
        patches.append({
            "patchIndex": patch_index,
            "headerRange": [header_start, coefficient_start],
            "coefficientRange": [coefficient_start, coefficient_end],
            "coefficientCount": coefficient_count,
        })
        coefficient_indices.extend(indices)
        cursor = coefficient_end
    if cursor != len(coefficients):
        raise RuntimeError(f"PCA layout did not consume array: {cursor} != {len(coefficients)}")
    return patches, coefficient_indices


def probe_all_face_coefficient_sensitivity_v128():
    if REPORT.exists():
        raise RuntimeError("refusing to overwrite immutable v128 report")
    character = unreal.load_asset(SOURCE)
    if character is None or character.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError(f"source MetaHuman Character unavailable: {SOURCE}")
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    if not subsystem.try_add_object_to_edit(character):
        raise RuntimeError("could not open v087 for read-only PCA probing")
    base_coefficients = None
    restored = False
    started = time.perf_counter()
    try:
        base_coefficients = list(subsystem.get_face_model_coefficients(character))
        base_landmarks = list(subsystem.get_face_landmarks(character))
        if len(base_landmarks) != 77:
            raise RuntimeError(f"unexpected landmark count: {len(base_landmarks)}")
        patches, coefficient_indices = parse_patch_layout_v128(base_coefficients)
        samples = []
        for coefficient_index in coefficient_indices:
            trial = list(base_coefficients)
            trial[coefficient_index] += EPSILON
            subsystem.set_face_model_coefficients(character, trial)
            landmarks = list(subsystem.get_face_landmarks(character))
            deltas = []
            for landmark_index, (before, after) in enumerate(zip(base_landmarks, landmarks)):
                dx = after.x - before.x
                dy = after.y - before.y
                dz = after.z - before.z
                magnitude = (dx * dx + dy * dy + dz * dz) ** 0.5
                if magnitude >= 0.0001:
                    deltas.append({
                        "landmarkIndex": landmark_index,
                        "deltaCm": [dx, dy, dz],
                        "magnitudeCm": magnitude,
                    })
            samples.append({
                "coefficientIndex": coefficient_index,
                "baseValue": base_coefficients[coefficient_index],
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
            "iteration": "v128",
            "state": "read-only-full-pca-sensitivity-matrix",
            "engine": "5.8",
            "sourceCharacter": SOURCE,
            "coefficientArrayLength": len(base_coefficients),
            "patchCount": len(patches),
            "actualCoefficientCount": len(coefficient_indices),
            "patches": patches,
            "epsilon": EPSILON,
            "elapsedSeconds": time.perf_counter() - started,
            "stateRestored": restored,
            "maximumRestorationErrorCm": restoration_error,
            "assetSaved": False,
            "samples": samples,
        }, indent=2) + "\n", encoding="utf-8")
    finally:
        if base_coefficients is not None and not restored:
            try:
                subsystem.set_face_model_coefficients(character, base_coefficients)
            except Exception as error:
                unreal.log_error(f"failed to restore PCA state: {error}")
        if subsystem.is_object_added_for_editing(character):
            subsystem.remove_object_to_edit(character)
    unreal.log(f"Gahyeon v128 PCA sensitivity matrix written: {REPORT}")
    unreal.SystemLibrary.quit_editor()


probe_all_face_coefficient_sensitivity_v128()
