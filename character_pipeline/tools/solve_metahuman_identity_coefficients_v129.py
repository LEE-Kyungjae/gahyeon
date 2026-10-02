#!/usr/bin/env python3
"""Solve a bounded native MetaHuman PCA proposal from measured identity defects."""

import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
MATRIX = ROOT / "artifacts/gahyeon-ch/iterations/v128-metahuman-pca-sensitivity-matrix/sensitivity-matrix.json"
LANDMARKS = ROOT / "artifacts/gahyeon-ch/iterations/v108-metahuman-sculpt-probe/sculpt-state.json"
OUTPUT = ROOT / "artifacts/gahyeon-ch/iterations/v129-metahuman-joint-identity-solve/coefficient-proposal.json"


def solve_metahuman_identity_coefficients_v129():
    if OUTPUT.exists():
        raise RuntimeError("refusing to overwrite immutable v129 proposal")
    matrix_report = json.loads(MATRIX.read_text(encoding="utf-8"))
    landmark_report = json.loads(LANDMARKS.read_text(encoding="utf-8"))
    if not matrix_report.get("stateRestored") or matrix_report.get("assetSaved"):
        raise RuntimeError("v128 is not a clean read-only sensitivity matrix")
    landmark_character = landmark_report["character"].split(".", 1)[0]
    if matrix_report["sourceCharacter"] != landmark_character:
        raise RuntimeError("sensitivity matrix and landmark baseline do not share a character")

    samples = matrix_report["samples"]
    coefficient_indices = [sample["coefficientIndex"] for sample in samples]
    epsilon = matrix_report["epsilon"]
    derivative = np.zeros((77, 3, len(samples)), dtype=np.float64)
    for column, sample in enumerate(samples):
        for delta in sample["landmarkDeltas"]:
            derivative[delta["landmarkIndex"], :, column] = np.asarray(delta["deltaCm"]) / epsilon

    # Preserve the already-close eye/upper-face geometry while solving measured lower-face defects.
    anchors = set(range(17, 27)) | set(range(33, 44)) | set(range(49, 60)) | {0, 6, 9, 12, 23, 25, 26, 40, 57, 58, 59, 69, 70, 73, 74, 75, 76}
    goals = {
        11: (0.0, 0.0, 0.90),
        44: (0.0, 0.0, 0.75),
        66: (0.0, 0.0, 0.75),
        1: (0.0, 0.0, 0.45),
        27: (0.0, 0.0, 0.45),
        2: (-0.08, 0.0, 0.0),
        28: (0.08, 0.0, 0.0),
        10: (-0.05, 0.0, 0.0),
        16: (0.05, 0.0, 0.0),
        4: (0.0, -0.18, 0.0),
        13: (0.0, -0.18, 0.0),
        63: (0.0, -0.18, 0.0),
        20: (0.0, 0.12, 0.0),
        53: (0.0, 0.12, 0.0),
    }
    rows = []
    targets = []
    labels = []
    for landmark_index in sorted(anchors | set(goals)):
        target = goals.get(landmark_index, (0.0, 0.0, 0.0))
        weight = 1.0 if landmark_index in goals else 0.35
        for axis in range(3):
            rows.append(derivative[landmark_index, axis, :] * weight)
            targets.append(target[axis] * weight)
            labels.append((landmark_index, axis))
    design = np.asarray(rows)
    target_vector = np.asarray(targets)
    ridge = 0.035
    # Solve the equivalent dual ridge system; constraints are far fewer than coefficients.
    dual = design @ design.T + ridge * np.eye(design.shape[0])
    solution = design.T @ np.linalg.solve(dual, target_vector)
    solution = np.clip(solution, -3.0, 3.0)
    prediction = design @ solution
    changes = []
    for column, delta in enumerate(solution):
        if abs(delta) >= 0.001:
            changes.append({
                "coefficientIndex": coefficient_indices[column],
                "baseValue": samples[column]["baseValue"],
                "delta": float(delta),
                "resultValue": float(samples[column]["baseValue"] + delta),
            })
    goal_results = []
    for landmark_index, requested in goals.items():
        predicted = derivative[landmark_index] @ solution
        goal_results.append({
            "landmarkIndex": landmark_index,
            "requestedDeltaCm": list(requested),
            "predictedDeltaCm": predicted.tolist(),
            "residualCm": (np.asarray(requested) - predicted).tolist(),
        })
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v129",
        "state": "bounded-pca-proposal-awaiting-native-application",
        "sourceCharacter": matrix_report["sourceCharacter"],
        "sensitivityMatrix": str(MATRIX.relative_to(ROOT)),
        "hypothesis": "A regularized joint PCA solve can shorten the overlong lower face while preserving the already-close eye geometry and correcting mouth, nose, cheek, and profile proportions together.",
        "action": "Solve a minimum-energy coefficient delta against explicit 3D landmark goals, preserving upper-face anchors and clipping every coefficient delta to +/-3.0.",
        "expectedResult": "Improve lower-face ratios and profile fullness without the single-region distortion or topology damage seen in rejected direct-mesh iterations.",
        "ridge": ridge,
        "coefficientDeltaLimit": 3.0,
        "changedCoefficientCount": len(changes),
        "coefficientChanges": changes,
        "goalResults": goal_results,
        "weightedRootMeanSquareResidualCm": float(np.sqrt(np.mean((prediction - target_vector) ** 2))),
        "automaticApproval": False,
        "productionReady": False,
    }, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    solve_metahuman_identity_coefficients_v129()
