#!/usr/bin/env python3
"""Solve an incremental MetaHuman PCA update from Epic-tracked canonical contours."""

import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
MATRIX = ROOT / "artifacts/gahyeon-ch/iterations/v128-metahuman-pca-sensitivity-matrix/sensitivity-matrix.json"
CURRENT = ROOT / "artifacts/gahyeon-ch/iterations/v129-metahuman-joint-identity-solve/coefficient-proposal.json"
MAPPING = ROOT / "artifacts/gahyeon-ch/iterations/v140-native-epic-corrected-map/mapping.json"
OUTPUT = ROOT / "artifacts/gahyeon-ch/iterations/v141-epic-contour-pca-solve/coefficient-proposal.json"


def solve_epic_contour_pca_v141():
    if OUTPUT.exists():
        raise RuntimeError("refusing to overwrite immutable v141 proposal")
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    current = json.loads(CURRENT.read_text(encoding="utf-8"))
    mapping = json.loads(MAPPING.read_text(encoding="utf-8"))
    samples = matrix["samples"]
    epsilon = matrix["epsilon"]
    derivative = np.zeros((77, 3, len(samples)), dtype=np.float64)
    for column, sample in enumerate(samples):
        for delta in sample["landmarkDeltas"]:
            derivative[delta["landmarkIndex"], :, column] = np.asarray(delta["deltaCm"]) / epsilon
    current_values = {sample["coefficientIndex"]: sample["baseValue"] for sample in samples}
    for change in current["coefficientChanges"]:
        current_values[change["coefficientIndex"]] = change["resultValue"]

    accepted = []
    goals = {}
    for entry in mapping["mappings"]:
        goal = np.asarray(entry["proposedDeltaXZCm"], dtype=float)
        if entry["currentAssociationDistancePixels"] <= 12.0 and np.max(np.abs(goal)) <= 0.60:
            goals[entry["landmarkIndex"]] = (goal[0], 0.0, goal[1])
            accepted.append(entry)
    # MediaPipe measurements still show a 5.6% long eye-line-to-chin ratio.
    # Move only jaw/chin points and explicitly keep nasal vertical positions anchored.
    goals.update({
        11: (0.0, 0.0, 0.80),
        44: (0.0, 0.0, 0.65),
        66: (0.0, 0.0, 0.65),
        1: (0.0, 0.0, 0.30),
        27: (0.0, 0.0, 0.30),
    })
    hard_anchors = {4, 10, 13, 16, 63}
    rows = []
    targets = []
    for landmark_index in range(77):
        if landmark_index in goals:
            target = goals[landmark_index]
            weight = 1.0
        elif landmark_index in hard_anchors:
            target = (0.0, 0.0, 0.0)
            weight = 0.8
        else:
            target = (0.0, 0.0, 0.0)
            weight = 0.12
        for axis in range(3):
            rows.append(derivative[landmark_index, axis, :] * weight)
            targets.append(target[axis] * weight)
    design = np.asarray(rows)
    target_vector = np.asarray(targets)
    ridge = 0.003
    dual = design @ design.T + ridge * np.eye(design.shape[0])
    solution = design.T @ np.linalg.solve(dual, target_vector)
    solution = np.clip(solution, -2.0, 2.0)
    changes = []
    coefficient_indices = [sample["coefficientIndex"] for sample in samples]
    for column, delta in enumerate(solution):
        if abs(delta) >= 0.001:
            index = coefficient_indices[column]
            base_value = current_values[index]
            changes.append({
                "coefficientIndex": index,
                "baseValue": base_value,
                "delta": float(delta),
                "resultValue": float(base_value + delta),
            })
    results = []
    for landmark_index, requested in sorted(goals.items()):
        predicted = derivative[landmark_index] @ solution
        results.append({
            "landmarkIndex": landmark_index,
            "requestedDeltaCm": list(requested),
            "predictedDeltaCm": predicted.tolist(),
        })
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v141",
        "state": "bounded-epic-contour-pca-proposal-awaiting-native-application",
        "sourceCharacter": "/Game/Gahyeon/CharacterPipeline/v130/Character/MHC_Gahyeon_JointIdentity_v130",
        "sensitivityMatrix": str(MATRIX.relative_to(ROOT)),
        "contourMapping": str(MAPPING.relative_to(ROOT)),
        "hypothesis": "Epic-tracked canonical eye and lip contours plus a partitioned jaw correction can improve identity without moving nasal height or relying on guessed eye landmarks.",
        "acceptedContourMappingCount": len(accepted),
        "rejectedContourMappingCount": len(mapping["mappings"]) - len(accepted),
        "associationDistanceLimitPixels": 12.0,
        "goalAxisLimitCm": 0.60,
        "ridge": ridge,
        "incrementalCoefficientDeltaLimit": 2.0,
        "changedCoefficientCount": len(changes),
        "coefficientChanges": changes,
        "goalResults": results,
        "automaticApproval": False,
        "productionReady": False,
    }, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    solve_epic_contour_pca_v141()
