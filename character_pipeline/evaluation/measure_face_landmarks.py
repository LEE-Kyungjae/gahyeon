#!/usr/bin/env python3
"""Extract normalized facial proportions with MediaPipe; never emit identity scores."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import cv2
import mediapipe as mp


INDEX = {
    "foreheadTop": 10, "chin": 152,
    "faceLeft": 234, "faceRight": 454,
    "leftEyeOuter": 33, "leftEyeInner": 133,
    "rightEyeInner": 362, "rightEyeOuter": 263,
    "noseLeft": 129, "noseRight": 358, "noseTip": 1,
    "mouthLeft": 61, "mouthRight": 291,
    "upperLip": 13, "lowerLip": 14,
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def distance(a, b) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def extract_measurements(path: Path) -> dict:
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
    points = {name: [raw[index].x * width, raw[index].y * height] for name, index in INDEX.items()}
    face_width = distance(points["faceLeft"], points["faceRight"])
    face_height = distance(points["foreheadTop"], points["chin"])
    if min(face_width, face_height) <= 1:
        raise ValueError("degenerate facial landmark scale")
    left_center = [(points["leftEyeOuter"][i] + points["leftEyeInner"][i]) / 2 for i in (0, 1)]
    right_center = [(points["rightEyeOuter"][i] + points["rightEyeInner"][i]) / 2 for i in (0, 1)]
    values = {
        "faceAspectWidthOverHeight": face_width / face_height,
        "eyeCenterSeparationOverFaceWidth": distance(left_center, right_center) / face_width,
        "leftEyeWidthOverFaceWidth": distance(points["leftEyeOuter"], points["leftEyeInner"]) / face_width,
        "rightEyeWidthOverFaceWidth": distance(points["rightEyeOuter"], points["rightEyeInner"]) / face_width,
        "noseWidthOverFaceWidth": distance(points["noseLeft"], points["noseRight"]) / face_width,
        "mouthWidthOverFaceWidth": distance(points["mouthLeft"], points["mouthRight"]) / face_width,
        "lipOpeningOverFaceHeight": distance(points["upperLip"], points["lowerLip"]) / face_height,
        "eyeLineToChinOverFaceHeight": (
            points["chin"][1] - (left_center[1] + right_center[1]) / 2
        ) / face_height,
        "noseTipToChinOverFaceHeight": (points["chin"][1] - points["noseTip"][1]) / face_height,
        "mouthToChinOverFaceHeight": (
            points["chin"][1] - (points["upperLip"][1] + points["lowerLip"][1]) / 2
        ) / face_height,
    }
    return {
        "schemaVersion": 1,
        "image": {"uri": str(path), "sha256": digest(path), "dimensions": [width, height]},
        "detector": {"name": "MediaPipe Face Mesh", "version": mp.__version__,
                     "landmarkCount": len(raw), "singleFaceDetected": True},
        "normalization": {"faceWidthIndices": [234, 454], "faceHeightIndices": [10, 152]},
        "measurements": {name: round(value, 6) for name, value in values.items()},
        "landmarksPixels": {name: [round(value, 3) for value in point] for name, point in points.items()},
        "qualityClaim": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--overlay", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite: {args.output}")
    result = extract_measurements(args.image.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.overlay:
        if args.overlay.exists():
            raise SystemExit(f"refusing to overwrite: {args.overlay}")
        image = cv2.imread(str(args.image.resolve()))
        for name, (x, y) in result["landmarksPixels"].items():
            point = (round(x), round(y))
            cv2.circle(image, point, 5, (0, 255, 255), -1, lineType=cv2.LINE_AA)
            cv2.putText(image, name, (point[0] + 7, point[1] - 7), cv2.FONT_HERSHEY_SIMPLEX,
                        0.38, (255, 255, 255), 1, cv2.LINE_AA)
        args.overlay.parent.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(str(args.overlay), image):
            raise SystemExit(f"cannot write overlay: {args.overlay}")
    print(json.dumps({"valid": True, "measurements": len(result["measurements"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
