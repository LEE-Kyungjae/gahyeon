"""Inspect Ururu animation curve names and morph metadata without mutating assets."""

from __future__ import annotations

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
ANIMATION_PATH = "/Game/LivingCharacterPOC/v708/Animation/UruruFace/Ururu_HeadMorphs_Centimeter_v688"
SKELETON_PATH = "/Game/LivingCharacterPOC/v585/Characters/UruruCentimeterNormalized/Ururu_CentimeterNormalized_v584_Skeleton"
REPORT = ROOT / "artifacts/living-character-poc-v711-ururu-curve-metadata-inspection/report.json"


def inspect_ururu_curve_metadata_v711() -> None:
    if REPORT.exists():
        raise RuntimeError("refusing to overwrite immutable v711 report")
    animation = unreal.load_asset(ANIMATION_PATH)
    skeleton = unreal.load_asset(SKELETON_PATH)
    if not isinstance(animation, unreal.AnimSequence) or skeleton is None:
        raise RuntimeError("v711 dependencies are unavailable")
    curve_names = [
        str(name)
        for name in unreal.AnimationBlueprintLibrary.get_animation_curve_names(
            animation, unreal.RawCurveTrackTypes.RCT_FLOAT
        )
    ]
    metadata_names = [str(name) for name in unreal.AnimationBlueprintLibrary.get_curve_meta_data_names(skeleton)]
    curves = []
    for name in curve_names:
        curves.append({
            "name": name,
            "morphTargetMetadata": bool(
                unreal.AnimationBlueprintLibrary.get_curve_meta_data_morph_target(skeleton, name)
            ),
            "materialMetadata": bool(
                unreal.AnimationBlueprintLibrary.get_curve_meta_data_material(skeleton, name)
            ),
            "valueAtExpectedPeak": float(
                unreal.AnimationBlueprintLibrary.get_float_value_at_time(
                    animation,
                    name,
                    {"EyeBlink_L": 10 / 24, "EyeBlink_R": 10 / 24, "GazeLeft": 20 / 24, "GazeRight": 30 / 24}.get(name, 0.0),
                )
            ),
        })
    report = {
        "schemaVersion": 1,
        "iteration": "v711",
        "status": "read-only-curve-metadata-inspection",
        "animation": ANIMATION_PATH,
        "skeleton": SKELETON_PATH,
        "curveNames": curve_names,
        "skeletonCurveMetadataNames": metadata_names,
        "curves": curves,
        "automaticApproval": False,
        "humanApproved": False,
        "productionReady": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.log("URURU_CURVE_METADATA_V711=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


inspect_ururu_curve_metadata_v711()
