#!/usr/bin/env python3
"""Map native MetaHuman landmarks to Epic contours and derive canonical X/Z goals."""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
TRACKING = ROOT / "artifacts/gahyeon-ch/iterations/v137-epic-face-contour-tracking/tracking-report.json"
BASE = ROOT / "artifacts/gahyeon-ch/iterations/v108-metahuman-sculpt-probe/sculpt-state.json"
DELTA = ROOT / "artifacts/gahyeon-ch/iterations/v130-metahuman-joint-identity-native/application-receipt.json"
OUTPUT = ROOT / "artifacts/gahyeon-ch/iterations/v139-native-epic-calibrated-map"
EYE_NEGATIVE_X = (49, 50, 51, 52, 53, 54, 55, 56)
EYE_POSITIVE_X = (17, 18, 19, 20, 21, 22, 23, 24)
LIPS = (2, 3, 8, 15, 28, 29, 30, 32, 41, 45, 46, 47, 48, 60, 61)


def similarity(source, target):
    source_center = source.mean(axis=0)
    target_center = target.mean(axis=0)
    source_zero = source - source_center
    target_zero = target - target_center
    u, singular, vt = np.linalg.svd(source_zero.T @ target_zero)
    rotation = u @ vt
    if np.linalg.det(rotation) < 0:
        u[:, -1] *= -1
        rotation = u @ vt
    scale = singular.sum() / np.square(source_zero).sum()
    translation = target_center - scale * source_center @ rotation
    return scale, rotation, translation


def apply_similarity(points, transform):
    scale, rotation, translation = transform
    return scale * points @ rotation + translation


def invert_similarity(points, transform):
    scale, rotation, translation = transform
    return ((points - translation) @ rotation.T) / scale


def contour_arrays(image):
    return {
        name: np.asarray([[point[0], -point[1]] for point in points], dtype=float)
        for name, points in image["contours"].items()
    }


def group_points(contours, predicate):
    return np.concatenate([points for name, points in contours.items() if predicate(name)])


def anchor_centers(contours):
    right_eye = group_points(contours, lambda name: "eyelid" in name and name.endswith("_r"))
    left_eye = group_points(contours, lambda name: "eyelid" in name and name.endswith("_l"))
    lips = group_points(contours, lambda name: "lip" in name)
    return np.asarray([right_eye.mean(axis=0), left_eye.mean(axis=0), lips.mean(axis=0)])


def nearest_contour(point, contours, allowed):
    best = None
    for name, points in contours.items():
        if not allowed(name):
            continue
        distances = np.linalg.norm(points - point, axis=1)
        index = int(np.argmin(distances))
        candidate = (float(distances[index]), name, index, points[index])
        if best is None or candidate[0] < best[0]:
            best = candidate
    return best


def build_calibrated_native_contour_map_v139():
    if OUTPUT.exists():
        raise RuntimeError("refusing to overwrite immutable v139 output")
    report = json.loads(TRACKING.read_text(encoding="utf-8"))
    base = json.loads(BASE.read_text(encoding="utf-8"))
    delta = json.loads(DELTA.read_text(encoding="utf-8"))
    native = np.asarray([entry["position"] for entry in base["landmarks"]], dtype=float)
    for entry in delta["measuredLandmarkDeltas"]:
        native[entry["landmarkIndex"]] += np.asarray(entry["deltaCm"])
    current = contour_arrays(report["images"]["metahumanV134"])
    canonical = contour_arrays(report["images"]["canonical03"])
    canonical_to_current = similarity(anchor_centers(canonical), anchor_centers(current))
    native_anchors = np.asarray([
        native[list(EYE_NEGATIVE_X)][:, (0, 2)].mean(axis=0),
        native[list(EYE_POSITIVE_X)][:, (0, 2)].mean(axis=0),
        native[list(LIPS)][:, (0, 2)].mean(axis=0),
    ])
    native_to_current = similarity(native_anchors, anchor_centers(current))

    mappings = []
    groups = (
        (EYE_NEGATIVE_X, lambda name: "eyelid" in name and name.endswith("_r"), "negative-x-eye"),
        (EYE_POSITIVE_X, lambda name: "eyelid" in name and name.endswith("_l"), "positive-x-eye"),
        (LIPS, lambda name: "lip" in name, "lips"),
    )
    for indices, allowed, group in groups:
        for landmark_index in indices:
            native_xz = native[landmark_index, (0, 2)]
            projected = apply_similarity(native_xz[None, :], native_to_current)[0]
            distance, curve, point_index, current_point = nearest_contour(projected, current, allowed)
            canonical_point = canonical[curve][point_index]
            canonical_in_current = apply_similarity(canonical_point[None, :], canonical_to_current)[0]
            target_native = invert_similarity(canonical_in_current[None, :], native_to_current)[0]
            goal = target_native - native_xz
            mappings.append({
                "landmarkIndex": landmark_index,
                "group": group,
                "curve": curve,
                "curvePointIndex": point_index,
                "currentAssociationDistancePixels": distance,
                "currentNativeXZCm": native_xz.tolist(),
                "canonicalTargetXZCm": target_native.tolist(),
                "proposedDeltaXZCm": goal.tolist(),
            })

    OUTPUT.mkdir(parents=True, exist_ok=False)
    fig, axis = plt.subplots(figsize=(10, 8), dpi=180)
    for name, points in current.items():
        color = "#4fc3f7" if "eyelid" in name else ("#ff6f91" if "lip" in name else "#66bb6a")
        axis.plot(points[:, 0], points[:, 1], color=color, linewidth=1.3, alpha=0.7)
    canonical_aligned = {name: apply_similarity(points, canonical_to_current) for name, points in canonical.items()}
    for name, points in canonical_aligned.items():
        color = "#b3e5fc" if "eyelid" in name else ("#ffc1d3" if "lip" in name else "#b9f6ca")
        axis.plot(points[:, 0], points[:, 1], color=color, linewidth=1.0, alpha=0.7, linestyle="--")
    for mapping in mappings:
        start = apply_similarity(np.asarray([mapping["currentNativeXZCm"]]), native_to_current)[0]
        end = apply_similarity(np.asarray([mapping["canonicalTargetXZCm"]]), native_to_current)[0]
        axis.scatter(start[0], start[1], s=18, color="#ffd54f", edgecolor="black", linewidth=0.3)
        axis.plot([start[0], end[0]], [start[1], end[1]], color="#ffca28", linewidth=0.7)
        axis.text(start[0] + 2, start[1] + 2, str(mapping["landmarkIndex"]), fontsize=6, color="white")
    axis.set_aspect("equal")
    axis.invert_yaxis()
    axis.set_facecolor("#151515")
    fig.patch.set_facecolor("#151515")
    axis.set_title("Epic contours: v134 solid, canonical aligned dashed; native goals yellow", color="white")
    axis.tick_params(colors="white")
    fig.tight_layout()
    fig.savefig(OUTPUT / "calibrated-contour-goals.png", facecolor=fig.get_facecolor())
    plt.close(fig)
    (OUTPUT / "mapping.json").write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v139",
        "state": "camera-normalized-front-contour-goals-awaiting-outlier-gate",
        "sourceCharacter": delta["character"],
        "trackingReport": str(TRACKING.relative_to(ROOT)),
        "mappingCount": len(mappings),
        "nativeToCurrentScalePixelsPerCm": native_to_current[0],
        "mappings": mappings,
        "limitations": [
            "Front-view similarity alignment constrains X/Z only and cannot infer depth Y.",
            "Nearest-curve association must be outlier-gated before PCA application.",
            "Epic image tracking exposes eyelid, lip, and nasolabial curves but no jaw or nose outline."
        ],
        "automaticApproval": False,
        "productionReady": False,
    }, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    build_calibrated_native_contour_map_v139()
