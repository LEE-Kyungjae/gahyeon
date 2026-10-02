#!/usr/bin/env python3
"""Visualize native MetaHuman landmarks against Epic's tracked image contours."""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
TRACKING = ROOT / "artifacts/gahyeon-ch/iterations/v137-epic-face-contour-tracking/tracking-report.json"
BASE = ROOT / "artifacts/gahyeon-ch/iterations/v108-metahuman-sculpt-probe/sculpt-state.json"
DELTA = ROOT / "artifacts/gahyeon-ch/iterations/v130-metahuman-joint-identity-native/application-receipt.json"
OUTPUT = ROOT / "artifacts/gahyeon-ch/iterations/v138-native-epic-contour-map"
EYE_LEFT = (49, 50, 51, 52, 53, 54, 55, 56)
EYE_RIGHT = (17, 18, 19, 20, 21, 22, 23, 24)
LOWER_CENTRAL = (2, 3, 4, 8, 10, 13, 14, 15, 16, 28, 29, 30, 32, 41, 45, 46, 47, 48, 60, 61, 62, 63, 64, 65, 68, 72)


def build_native_to_epic_contour_map_v138():
    if OUTPUT.exists():
        raise RuntimeError("refusing to overwrite immutable v138 output")
    tracking = json.loads(TRACKING.read_text(encoding="utf-8"))
    base = json.loads(BASE.read_text(encoding="utf-8"))
    delta = json.loads(DELTA.read_text(encoding="utf-8"))
    native = np.asarray([entry["position"] for entry in base["landmarks"]], dtype=float)
    for entry in delta["measuredLandmarkDeltas"]:
        native[entry["landmarkIndex"]] += np.asarray(entry["deltaCm"])
    contours = tracking["images"]["metahumanV134"]["contours"]
    contour_points = {
        name: np.asarray([[point[0], -point[1]] for point in points], dtype=float)
        for name, points in contours.items()
    }
    tracked_all = np.concatenate(list(contour_points.values()))
    selected_indices = EYE_LEFT + EYE_RIGHT + LOWER_CENTRAL
    native_xz = native[list(selected_indices)][:, (0, 2)]
    # A global similarity normalization is sufficient for correspondence inspection;
    # it deliberately does not claim exact camera calibration.
    native_center = native_xz.mean(axis=0)
    tracked_center = tracked_all.mean(axis=0)
    native_scale = np.linalg.norm(native_xz.max(axis=0) - native_xz.min(axis=0))
    tracked_scale = np.linalg.norm(tracked_all.max(axis=0) - tracked_all.min(axis=0))
    normalized_native = (native_xz - native_center) / native_scale
    normalized_contours = {
        name: (points - tracked_center) / tracked_scale for name, points in contour_points.items()
    }

    OUTPUT.mkdir(parents=True, exist_ok=False)
    fig, axis = plt.subplots(figsize=(10, 10), dpi=180)
    for name, points in normalized_contours.items():
        color = "#4fc3f7" if "eyelid" in name else ("#ff6f91" if "lip" in name else "#66bb6a")
        axis.plot(points[:, 0], points[:, 1], color=color, linewidth=1.5, alpha=0.85)
    for index, point in zip(selected_indices, normalized_native):
        axis.scatter(point[0], point[1], s=20, color="#ffd54f", edgecolor="black", linewidth=0.4)
        axis.text(point[0] + 0.004, point[1] + 0.004, str(index), fontsize=7, color="white")
    axis.set_aspect("equal")
    axis.set_facecolor("#151515")
    fig.patch.set_facecolor("#151515")
    axis.set_title("v130 native 77 landmarks (yellow) vs v134 Epic image contours", color="white")
    axis.tick_params(colors="white")
    for spine in axis.spines.values():
        spine.set_color("white")
    fig.tight_layout()
    fig.savefig(OUTPUT / "native-vs-epic-contours.png", facecolor=fig.get_facecolor())
    plt.close(fig)
    (OUTPUT / "manifest.json").write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v138",
        "state": "visual-correspondence-audit-not-calibrated-projection",
        "nativeCharacter": delta["character"],
        "trackingReport": str(TRACKING.relative_to(ROOT)),
        "selectedNativeIndices": list(selected_indices),
        "normalization": "independent global center and diagonal scale; inspection only",
        "image": "native-vs-epic-contours.png",
        "automaticApproval": False,
        "productionReady": False,
    }, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    build_native_to_epic_contour_map_v138()
