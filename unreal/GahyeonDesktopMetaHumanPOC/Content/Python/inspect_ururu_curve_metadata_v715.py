"""Inspect known Ururu curve metadata with typed UE 5.8 curve identifiers."""

from __future__ import annotations

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SKELETON_PATH = "/Game/LivingCharacterPOC/v585/Characters/UruruCentimeterNormalized/Ururu_CentimeterNormalized_v584_Skeleton"
REPORT = ROOT / "artifacts/living-character-poc-v715-ururu-curve-metadata-inspection/report.json"
CURVES = ("EyeBlink_L", "EyeBlink_R", "GazeLeft", "GazeRight")


def inspect_ururu_curve_metadata_v715() -> None:
    if REPORT.exists():
        raise RuntimeError("refusing to overwrite immutable v715 report")
    skeleton = unreal.load_asset(SKELETON_PATH)
    if skeleton is None:
        raise RuntimeError("validated v585 skeleton is unavailable")
    curves = []
    for name in CURVES:
        identifier = skeleton.find_curve_identifier(name, unreal.RawCurveTrackTypes.RCT_FLOAT)
        curves.append({
            "name": name,
            "identifier": str(identifier),
            "morphTargetMetadata": bool(skeleton.get_curve_meta_data_morph_target(name)),
            "materialMetadata": bool(skeleton.get_curve_meta_data_material(name)),
        })
    report = {
        "schemaVersion": 1,
        "iteration": "v715",
        "status": "read-only-skeleton-curve-metadata-inspection",
        "skeleton": SKELETON_PATH,
        "metadataNames": [str(name) for name in skeleton.get_curve_meta_data_names()],
        "curves": curves,
        "animationLibraryMembers": sorted(name for name in dir(unreal.AnimationLibrary) if "curve" in name.lower()),
        "automaticApproval": False,
        "humanApproved": False,
        "productionReady": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.log("URURU_CURVE_METADATA_V715=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


inspect_ururu_curve_metadata_v715()
