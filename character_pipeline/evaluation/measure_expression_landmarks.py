#!/usr/bin/env python3
"""Measure expression geometry without assigning an expression label or quality score."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import cv2
import mediapipe as mp


POINTS = {
    "faceLeft": 234, "faceRight": 454, "foreheadTop": 10, "chin": 152,
    "leftEyeUpper": 159, "leftEyeLower": 145, "leftEyeOuter": 33, "leftEyeInner": 133,
    "rightEyeUpper": 386, "rightEyeLower": 374, "rightEyeOuter": 263, "rightEyeInner": 362,
    "mouthLeft": 61, "mouthRight": 291, "upperLip": 13, "lowerLip": 14,
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def extract_expression_measurements(path: Path) -> dict:
    image = cv2.imread(str(path))
    if image is None:
        raise ValueError(f"cannot read image: {path}")
    height, width = image.shape[:2]
    with mp.solutions.face_mesh.FaceMesh(
        static_image_mode=True, max_num_faces=1, refine_landmarks=True,
        min_detection_confidence=0.3,
    ) as detector:
        result = detector.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    if not result.multi_face_landmarks or len(result.multi_face_landmarks) != 1:
        raise ValueError("expected exactly one detected face")
    raw = result.multi_face_landmarks[0].landmark
    points = {name: (raw[index].x * width, raw[index].y * height) for name, index in POINTS.items()}
    face_width = distance(points["faceLeft"], points["faceRight"])
    face_height = distance(points["foreheadTop"], points["chin"])
    mouth_width = distance(points["mouthLeft"], points["mouthRight"])
    left_eye_width = distance(points["leftEyeOuter"], points["leftEyeInner"])
    right_eye_width = distance(points["rightEyeOuter"], points["rightEyeInner"])
    if min(face_width, face_height, mouth_width, left_eye_width, right_eye_width) <= 1:
        raise ValueError("degenerate facial landmark scale")
    mouth_mid_y = (points["upperLip"][1] + points["lowerLip"][1]) / 2
    values = {
        "mouthOpeningOverFaceHeight": distance(points["upperLip"], points["lowerLip"]) / face_height,
        "mouthWidthOverFaceWidth": mouth_width / face_width,
        "mouthCornerLiftLeftOverFaceHeight": (mouth_mid_y - points["mouthLeft"][1]) / face_height,
        "mouthCornerLiftRightOverFaceHeight": (mouth_mid_y - points["mouthRight"][1]) / face_height,
        "leftEyeOpeningOverEyeWidth": distance(points["leftEyeUpper"], points["leftEyeLower"]) / left_eye_width,
        "rightEyeOpeningOverEyeWidth": distance(points["rightEyeUpper"], points["rightEyeLower"]) / right_eye_width,
    }
    return {
        "schemaVersion": 1,
        "image": {"uri": str(path), "sha256": digest(path), "dimensions": [width, height]},
        "detector": {"name": "MediaPipe Face Mesh", "version": mp.__version__,
                     "landmarkCount": len(raw), "singleFaceDetected": True},
        "measurements": {key: round(value, 6) for key, value in values.items()},
        "interpretation": {
            "expressionLabel": None,
            "qualityScore": None,
            "warning": "Metrics support human-reviewed labels; they do not establish emotion or viseme authority."
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite: {args.output}")
    result = extract_expression_measurements(args.image.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"valid": True, "measurements": len(result["measurements"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
