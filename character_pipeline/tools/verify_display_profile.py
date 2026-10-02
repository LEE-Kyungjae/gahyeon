#!/usr/bin/env python3

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("profile", type=Path)
    args = parser.parse_args()
    value = json.loads(args.profile.read_text(encoding="utf-8"))
    if value.get("profileId") != "looking-glass-go":
        raise SystemExit("unsupported display profile")
    if value.get("device", {}).get("panelResolution") != [1440, 2560]:
        raise SystemExit("Looking Glass Go panel resolution must be 1440x2560")
    if value.get("qa", {}).get("singleViewResolution") != [1440, 2560]:
        raise SystemExit("single-view QA must match the Go panel aspect and resolution")
    quilt = value.get("quilt", {})
    if quilt.get("viewCount") != 66:
        raise SystemExit("pinned Unreal profile requires 66 views")
    if any(quilt.get(key) is not None for key in ("columns", "rows", "resolution")):
        raise SystemExit("quilt geometry must come from connected-device calibration")
    if quilt.get("failClosedWithoutCalibration") is not True:
        raise SystemExit("quilt rendering must fail closed without calibration")
    print(json.dumps({"valid": True, "panel": [1440, 2560], "views": 66,
                      "quiltCalibrationRequired": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
