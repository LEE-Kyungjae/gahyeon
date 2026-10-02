"""Discover UE 5.8 reflected curve and asset-registry members without mutation."""

from __future__ import annotations

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
ANIMATION_PATH = "/Game/LivingCharacterPOC/v708/Animation/UruruFace/Ururu_HeadMorphs_Centimeter_v688"
REPORT = ROOT / "artifacts/living-character-poc-v713-ururu-curve-reflection/report.json"


def inspect_ururu_curve_reflection_v713() -> None:
    if REPORT.exists():
        raise RuntimeError("refusing to overwrite immutable v713 report")
    animation = unreal.load_asset(ANIMATION_PATH)
    if not isinstance(animation, unreal.AnimSequence):
        raise RuntimeError("v708 AnimSequence is unavailable")
    asset_data = unreal.AssetRegistryHelpers.create_asset_data(animation)
    report = {
        "schemaVersion": 1,
        "iteration": "v713",
        "status": "read-only-curve-reflection-discovery",
        "unrealModuleCandidates": sorted(
            name for name in dir(unreal)
            if any(token in name.lower() for token in ("animation", "curve", "skeleton"))
        ),
        "animationCurveMembers": sorted(name for name in dir(animation) if "curve" in name.lower()),
        "skeletonCurveMembers": sorted(
            name for name in dir(animation.get_editor_property("skeleton")) if "curve" in name.lower()
        ),
        "assetDataMembers": sorted(name for name in dir(asset_data) if "tag" in name.lower()),
        "automaticApproval": False,
        "humanApproved": False,
        "productionReady": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.log("URURU_CURVE_REFLECTION_V713=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


inspect_ururu_curve_reflection_v713()
