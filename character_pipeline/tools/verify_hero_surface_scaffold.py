#!/usr/bin/env python3
"""Verify the pending skin/eye QA contract without claiming production assets."""

import json
from pathlib import Path


def main() -> int:
    config = json.loads(Path("character_pipeline/config/hero_surface_qa.json").read_text())
    binding = json.loads(Path("character_pipeline/metahuman/validation/v001/surface-binding.json").read_text())
    if config["displayProfile"] != "looking-glass-go" or config["resolution"] != [1440, 2560]:
        raise SystemExit("invalid Go surface QA profile")
    if len(config["skin"]["requiredChannels"]) != 8 or len(config["skin"]["requiredZones"]) != 8:
        raise SystemExit("incomplete skin contract")
    if len(config["eyes"]["requiredParts"]) != 6 or len(config["eyes"]["requiredChecks"]) != 10:
        raise SystemExit("incomplete eye contract")
    if binding["state"] != "awaiting-metahuman-candidate" or binding["claim"] != "no-production-surface-assets-yet":
        raise SystemExit("pending binding overclaims production surface")
    if binding["legacyEvidence"]["acceptedAsProduction"] is not False:
        raise SystemExit("legacy diffuse was promoted")
    if binding["legacyEvidence"]["skinAlbedoResolution"] != [2048, 2048]:
        raise SystemExit("legacy skin audit drifted")
    print(json.dumps({"valid": True, "skinChannels": 8, "skinZones": 8,
                      "eyeParts": 6, "eyeChecks": 10, "captures": 7,
                      "state": binding["state"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
