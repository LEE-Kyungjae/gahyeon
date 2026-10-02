#!/usr/bin/env python3
"""Verify pending modular clothing QA without promoting the G1 blockout."""

import json
from pathlib import Path


def verify_clothing_scaffold(config: dict, binding: dict) -> dict:
    if config["displayProfile"] != "looking-glass-go" or config["resolution"] != [1440, 2560]:
        raise ValueError("invalid Go clothing profile")
    if len(config["requiredSlots"]) != 4 or len(config["requiredAssets"]) != 5:
        raise ValueError("incomplete modular clothing contract")
    if len(config["runtimeChecks"]) != 14 or len(config["captures"]) != 16:
        raise ValueError("incomplete clothing runtime/capture contract")
    if binding["state"] != "awaiting-production-clothing" or binding["claim"] != "no-production-clothing-yet":
        raise ValueError("pending clothing binding overclaims production")
    legacy = binding["legacyEvidence"]
    if legacy["acceptedAsProduction"] is not False or legacy["chaosCloth"] is not False:
        raise ValueError("legacy G1 clothing was promoted")
    if legacy["bodyAndClothingSeparateObjects"] is not True:
        raise ValueError("valuable G1 modular separation was lost")
    return {"valid": True, "slots": 4, "assets": 5, "runtimeChecks": 14,
            "captures": 16, "state": binding["state"]}


def main() -> int:
    config = json.loads(Path("character_pipeline/config/hero_clothing_qa.json").read_text())
    binding = json.loads(Path("character_pipeline/metahuman/validation/v001/clothing-binding.json").read_text())
    print(json.dumps(verify_clothing_scaffold(config, binding)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
