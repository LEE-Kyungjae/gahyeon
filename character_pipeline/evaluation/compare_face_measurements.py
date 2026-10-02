#!/usr/bin/env python3
"""Compare normalized landmark measurements without fabricating similarity scores."""

import argparse
import json
from pathlib import Path


LOW_CONFIDENCE_WITH_PROTOTYPE_EYES = {
    "eyeCenterSeparationOverFaceWidth", "leftEyeWidthOverFaceWidth",
    "rightEyeWidthOverFaceWidth", "eyeLineToChinOverFaceHeight",
}


def compare(reference: dict, candidate: dict, *, prototype_eyes: bool) -> dict:
    ref, current = reference["measurements"], candidate["measurements"]
    if set(ref) != set(current):
        raise ValueError("measurement sets differ")
    deltas = []
    for name in sorted(ref):
        absolute = current[name] - ref[name]
        relative = absolute / ref[name] if ref[name] else None
        deltas.append({
            "measurement": name, "reference": ref[name], "candidate": current[name],
            "absoluteDelta": round(absolute, 6),
            "relativeDeltaPercent": None if relative is None else round(relative * 100, 3),
            "confidence": "low" if prototype_eyes and name in LOW_CONFIDENCE_WITH_PROTOTYPE_EYES else "medium",
        })
    return {
        "schemaVersion": 1, "method": "normalized-mediapipe-landmark-delta-v1",
        "referenceImage": reference["image"], "candidateImage": candidate["image"],
        "prototypeEyes": prototype_eyes, "deltas": deltas,
        "identitySimilarityScore": None,
        "limitations": [
            "2D landmarks do not measure depth or profile identity",
            "hair, perspective and detector bias can alter face contour landmarks",
            "prototype eye geometry lowers confidence for eye-related measurements",
            "human review against canonical images 03/06/07/08 remains mandatory"
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("reference", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--prototype-eyes", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite: {args.output}")
    value = compare(
        json.loads(args.reference.read_text(encoding="utf-8")),
        json.loads(args.candidate.read_text(encoding="utf-8")),
        prototype_eyes=args.prototype_eyes,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"valid": True, "deltas": len(value["deltas"]), "identitySimilarityScore": None}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
