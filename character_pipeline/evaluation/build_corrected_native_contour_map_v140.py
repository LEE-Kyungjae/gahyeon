#!/usr/bin/env python3
"""Rebuild the Epic contour map with visually audited native eyelid indices."""

import json

import build_calibrated_native_contour_map_v139 as mapping


def build_corrected_native_contour_map_v140():
    mapping.OUTPUT = mapping.ROOT / "artifacts/gahyeon-ch/iterations/v140-native-epic-corrected-map"
    mapping.EYE_NEGATIVE_X = (21, 31, 42, 49, 50, 51)
    mapping.EYE_POSITIVE_X = (18, 19, 33, 34, 35, 38)
    mapping.build_calibrated_native_contour_map_v139()
    report_path = mapping.OUTPUT / "mapping.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["iteration"] = "v140"
    report["state"] = "visually-audited-front-contour-goals-awaiting-distance-gate"
    report["supersedes"] = "v139 eye-index classification"
    report["auditedEyeIndices"] = {
        "negativeX": list(mapping.EYE_NEGATIVE_X),
        "positiveX": list(mapping.EYE_POSITIVE_X),
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    build_corrected_native_contour_map_v140()
