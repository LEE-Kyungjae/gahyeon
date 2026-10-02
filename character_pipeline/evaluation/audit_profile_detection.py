#!/usr/bin/env python3
"""Audit profile landmark detectability and fail closed when candidate detection fails."""

import argparse
import hashlib
import json
from pathlib import Path

import cv2
import mediapipe as mp


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def detect(path: Path, detector) -> dict:
    image = cv2.imread(str(path))
    if image is None:
        raise ValueError(f"cannot read image: {path}")
    result = detector.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    faces = result.multi_face_landmarks or []
    return {"uri": str(path), "sha256": digest(path), "dimensions": [image.shape[1], image.shape[0]],
            "detectedFaces": len(faces), "landmarkCount": len(faces[0].landmark) if len(faces) == 1 else 0}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--canonical-left", type=Path, required=True)
    parser.add_argument("--candidate-left", type=Path, required=True)
    parser.add_argument("--canonical-right", type=Path, required=True)
    parser.add_argument("--candidate-right", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite: {args.output}")
    with mp.solutions.face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1,
                                         refine_landmarks=True, min_detection_confidence=0.2) as detector:
        records = {name: detect(getattr(args, name), detector) for name in
                   ("canonical_left", "candidate_left", "canonical_right", "candidate_right")}
    canonical_valid = all(records[name]["landmarkCount"] == 478 for name in ("canonical_left", "canonical_right"))
    candidate_valid = all(records[name]["landmarkCount"] == 478 for name in ("candidate_left", "candidate_right"))
    report = {"schemaVersion": 1, "detector": {"name": "MediaPipe Face Mesh", "version": mp.__version__},
              "records": records, "canonicalProfilesDetectable": canonical_valid,
              "candidateProfilesDetectable": candidate_valid,
              "automatedProfileComparisonAllowed": canonical_valid and candidate_valid,
              "identitySimilarityScore": None,
              "decision": "manual-profile-review-required" if not candidate_valid else "measurement-allowed"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"canonical": canonical_valid, "candidate": candidate_valid,
                      "automatedProfileComparisonAllowed": report["automatedProfileComparisonAllowed"]}))
    return 0 if report["automatedProfileComparisonAllowed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
