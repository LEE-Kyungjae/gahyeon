#!/usr/bin/env python3
"""Verify pending Groom QA without promoting the Blender blockout."""

import json
from pathlib import Path


def verify_groom_scaffold(config: dict, binding: dict) -> dict:
    if config["displayProfile"] != "looking-glass-go" or config["resolution"] != [1440, 2560]:
        raise ValueError("invalid Go Groom profile")
    if len(config["requiredGroups"]) != 4 or len(config["requiredFeatures"]) != 8:
        raise ValueError("incomplete Groom semantic contract")
    if len(config["runtimeChecks"]) != 10 or len(config["captures"]) != 14:
        raise ValueError("incomplete Groom runtime/capture contract")
    if binding["state"] != "awaiting-production-groom" or binding["claim"] != "no-production-groom-yet":
        raise ValueError("pending Groom binding overclaims production")
    legacy = binding["legacyEvidence"]
    if legacy["acceptedAsProduction"] is not False or legacy["unrealGroomAsset"] is not False:
        raise ValueError("legacy Blender groom was promoted")
    if legacy["guideCurves"] != 252 or legacy["evaluatedCurves"] != 10191:
        raise ValueError("legacy Groom audit drifted")
    return {"valid": True, "groups": 4, "features": 8, "runtimeChecks": 10,
            "captures": 14, "state": binding["state"]}


def main() -> int:
    config = json.loads(Path("character_pipeline/config/hero_groom_qa.json").read_text())
    binding = json.loads(Path("character_pipeline/metahuman/validation/v001/groom-binding.json").read_text())
    print(json.dumps(verify_groom_scaffold(config, binding)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
