#!/usr/bin/env python3
"""Verify the pending exact-frame diagnostic contract."""

import json
from pathlib import Path


def verify_deformation_diagnostics_scaffold(config: dict, cases: dict, report: dict) -> dict:
    if config["displayProfile"] != "looking-glass-go" or config["resolution"] != [1440, 2560]:
        raise ValueError("diagnostics are not bound to Looking Glass Go")
    frames = [(case["id"], frame) for case in cases["requiredCases"] for frame in case["frames"]]
    if len(cases["requiredCases"]) != 15 or len(frames) != 45 or len(set(frames)) != 45:
        raise ValueError("deformation cases must define 45 unique samples")
    if set(config["diagnostics"]) != {
        "lipPenetrationMm", "lipSealGapMm", "eyelidEyeballGapMm", "eyelidPenetrationMm",
        "mouthCornerAreaLossPercent", "cheekVolumeLossPercent", "neckStretchRatio",
        "shoulderVolumeLossPercent", "eyeAimErrorDegrees", "meshClippingPairs",
        "temporalVertexJumpMm",
    }:
        raise ValueError("deformation diagnostic contract is incomplete")
    if report["state"] != "awaiting-editor-capture" or report["editorRuntimeVerified"] is not False:
        raise ValueError("pending report overclaims Editor diagnostics")
    if report["samples"] or report["summary"] is not None or report["qualityClaim"] is not None:
        raise ValueError("pending report contains fabricated evidence")
    return {"valid": True, "cases": 15, "frames": 45, "diagnostics": 11,
            "state": report["state"]}


def main() -> int:
    config = json.loads(Path("character_pipeline/config/deformation_diagnostics.json").read_text())
    cases = json.loads(Path("character_pipeline/config/deformation_qa.json").read_text())
    report = json.loads(Path("character_pipeline/metahuman/validation/v001/deformation-diagnostics.json").read_text())
    print(json.dumps(verify_deformation_diagnostics_scaffold(config, cases, report)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
