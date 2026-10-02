#!/usr/bin/env python3
"""Extract normalized body proportions with MediaPipe Pose; emit no quality score."""

import argparse
import hashlib
import json
import math
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np


NAMES = {0: "nose", 11: "leftShoulder", 12: "rightShoulder", 13: "leftElbow",
         14: "rightElbow", 15: "leftWrist", 16: "rightWrist", 23: "leftHip",
         24: "rightHip", 25: "leftKnee", 26: "rightKnee", 27: "leftAnkle", 28: "rightAnkle"}


def distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def midpoint(a, b):
    return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract_body_measurements(path: Path) -> dict:
    image = cv2.imread(str(path))
    if image is None:
        raise ValueError(f"cannot read image: {path}")
    height, width = image.shape[:2]
    with mp.solutions.pose.Pose(static_image_mode=True, model_complexity=2,
                                enable_segmentation=True, min_detection_confidence=.25) as detector:
        result = detector.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    if result.pose_landmarks is None or result.segmentation_mask is None:
        raise ValueError("pose or segmentation was not detected")
    raw = result.pose_landmarks.landmark
    points = {name: (raw[index].x * width, raw[index].y * height) for index, name in NAMES.items()}
    mask = result.segmentation_mask > .5
    ys, xs = np.where(mask)
    if not len(xs):
        raise ValueError("empty person segmentation")
    silhouette_height = float(ys.max() - ys.min() + 1)
    shoulder_mid = midpoint(points["leftShoulder"], points["rightShoulder"])
    hip_mid = midpoint(points["leftHip"], points["rightHip"])
    torso = distance(shoulder_mid, hip_mid)
    left_leg = distance(points["leftHip"], points["leftKnee"]) + distance(points["leftKnee"], points["leftAnkle"])
    right_leg = distance(points["rightHip"], points["rightKnee"]) + distance(points["rightKnee"], points["rightAnkle"])
    left_arm = distance(points["leftShoulder"], points["leftElbow"]) + distance(points["leftElbow"], points["leftWrist"])
    right_arm = distance(points["rightShoulder"], points["rightElbow"]) + distance(points["rightElbow"], points["rightWrist"])
    values = {
        "shoulderWidthOverSilhouetteHeight": distance(points["leftShoulder"], points["rightShoulder"]) / silhouette_height,
        "hipWidthOverSilhouetteHeight": distance(points["leftHip"], points["rightHip"]) / silhouette_height,
        "torsoLengthOverSilhouetteHeight": torso / silhouette_height,
        "legLengthOverSilhouetteHeight": ((left_leg + right_leg) / 2) / silhouette_height,
        "armLengthOverSilhouetteHeight": ((left_arm + right_arm) / 2) / silhouette_height,
        "shoulderToHipWidthRatio": distance(points["leftShoulder"], points["rightShoulder"]) / distance(points["leftHip"], points["rightHip"]),
        "legToTorsoRatio": ((left_leg + right_leg) / 2) / torso,
        "upperToLowerLegRatio": ((distance(points["leftHip"], points["leftKnee"]) + distance(points["rightHip"], points["rightKnee"])) /
                                 (distance(points["leftKnee"], points["leftAnkle"]) + distance(points["rightKnee"], points["rightAnkle"]))),
    }
    visibility = {name: round(raw[index].visibility, 6) for index, name in NAMES.items()}
    return {"schemaVersion": 1, "image": {"uri": str(path), "sha256": digest(path), "dimensions": [width, height]},
            "detector": {"name": "MediaPipe Pose Heavy", "version": mp.__version__, "landmarkCount": len(raw)},
            "segmentationBoundsPixels": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
            "measurements": {key: round(value, 6) for key, value in values.items()},
            "landmarksPixels": {key: [round(v, 3) for v in value] for key, value in points.items()},
            "visibility": visibility, "qualityClaim": None}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--overlay", type=Path)
    args = parser.parse_args()
    if args.output.exists() or (args.overlay and args.overlay.exists()):
        raise SystemExit("refusing to overwrite body measurement output")
    result = extract_body_measurements(args.image.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    if args.overlay:
        image = cv2.imread(str(args.image.resolve()))
        for name, value in result["landmarksPixels"].items():
            point = tuple(round(v) for v in value)
            cv2.circle(image, point, 6, (0, 255, 255), -1)
            cv2.putText(image, name, (point[0] + 8, point[1] - 8), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
        args.overlay.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(args.overlay), image)
    print(json.dumps({"valid": True, "measurements": len(result["measurements"])}))


if __name__ == "__main__":
    main()
