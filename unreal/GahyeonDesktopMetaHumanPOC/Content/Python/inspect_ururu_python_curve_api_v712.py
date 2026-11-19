"""Discover UE 5.8's reflected animation-curve API and registry metadata."""

from __future__ import annotations

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
ANIMATION_PATH = "/Game/LivingCharacterPOC/v708/Animation/UruruFace/Ururu_HeadMorphs_Centimeter_v688"
REPORT = ROOT / "artifacts/living-character-poc-v712-ururu-python-curve-api/report.json"


def inspect_ururu_python_curve_api_v712() -> None:
    if REPORT.exists():
        raise RuntimeError("refusing to overwrite immutable v712 report")
    animation = unreal.load_asset(ANIMATION_PATH)
    if not isinstance(animation, unreal.AnimSequence):
        raise RuntimeError("v708 AnimSequence is unavailable")
    module_names = sorted(
        name for name in dir(unreal)
        if any(token in name.lower() for token in ("animation", "curve", "skeleton"))
    )
    asset_data = unreal.AssetRegistryHelpers.get_asset_registry().get_asset_by_object_path(animation.get_path_name())
    tags = {}
    for key in asset_data.tags_and_values.keys():
        value = asset_data.get_tag_value(str(key))
        tags[str(key)] = str(value) if value is not None else None
    report = {
        "schemaVersion": 1,
        "iteration": "v712",
        "status": "read-only-python-curve-api-discovery",
        "animation": ANIMATION_PATH,
        "unrealModuleCandidates": module_names,
        "assetRegistryTags": tags,
        "animationCurveMembers": sorted(name for name in dir(animation) if "curve" in name.lower()),
        "skeletonCurveMembers": sorted(
            name for name in dir(animation.get_editor_property("skeleton")) if "curve" in name.lower()
        ),
        "automaticApproval": False,
        "humanApproved": False,
        "productionReady": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.log("URURU_PYTHON_CURVE_API_V712=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


inspect_ururu_python_curve_api_v712()
