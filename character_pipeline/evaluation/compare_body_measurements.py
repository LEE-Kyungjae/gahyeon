#!/usr/bin/env python3
"""Compare pose-derived body ratios with explicit confidence and no score."""

import argparse
import json
from pathlib import Path


LOW = {"armLengthOverSilhouetteHeight", "hipWidthOverSilhouetteHeight", "shoulderToHipWidthRatio"}


def compare(reference, candidate):
    if set(reference["measurements"]) != set(candidate["measurements"]):
        raise ValueError("body measurement sets differ")
    deltas = []
    for name in sorted(reference["measurements"]):
        a, b = reference["measurements"][name], candidate["measurements"][name]
        deltas.append({"measurement": name, "reference": a, "candidate": b,
                       "absoluteDelta": round(b - a, 6), "relativeDeltaPercent": round((b - a) / a * 100, 3),
                       "confidence": "low" if name in LOW else "medium"})
    return {"schemaVersion": 1, "method": "mediapipe-pose-ratio-delta-v1", "deltas": deltas,
            "bodySimilarityScore": None,
            "limitations": ["reference and candidate poses differ", "clothing affects segmentation and joint detection",
                            "2D ratios do not measure body depth", "human review remains mandatory"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("reference", type=Path); parser.add_argument("candidate", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): raise SystemExit(f"refusing to overwrite: {args.output}")
    value = compare(json.loads(args.reference.read_text()), json.loads(args.candidate.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(value, indent=2) + "\n")
    print(json.dumps({"valid": True, "deltas": len(value["deltas"]), "bodySimilarityScore": None}))


if __name__ == "__main__": main()
