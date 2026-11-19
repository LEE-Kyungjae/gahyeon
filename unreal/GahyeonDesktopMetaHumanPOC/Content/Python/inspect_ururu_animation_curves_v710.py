"""Inspect the reflected curve payload of the immutable v708 Ururu AnimSequence."""

from __future__ import annotations

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
ANIMATION_PATH = "/Game/LivingCharacterPOC/v708/Animation/UruruFace/Ururu_HeadMorphs_Centimeter_v688"
REPORT = ROOT / "artifacts/living-character-poc-v710-ururu-animation-curve-inspection/report.json"


def _safe(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [_safe(item) for item in value]
    try:
        return str(value)
    except Exception:
        return f"<{type(value).__name__}>"


def inspect_ururu_animation_curves_v710() -> None:
    if REPORT.exists():
        raise RuntimeError("refusing to overwrite immutable v710 report")
    animation = unreal.load_asset(ANIMATION_PATH)
    if not isinstance(animation, unreal.AnimSequence):
        raise RuntimeError("v708 AnimSequence is unavailable")
    model = animation.get_editor_property("data_model_interface")
    if model is None:
        raise RuntimeError("v708 AnimSequence has no data model interface")

    methods = sorted(name for name in dir(model) if "curve" in name.lower())
    properties = {}
    for name in ("curve_data", "animated_bone_attributes"):
        try:
            properties[name] = _safe(model.get_editor_property(name))
        except Exception as exc:
            properties[name] = {"error": str(exc)}
    calls = {}
    for name in methods:
        method = getattr(model, name, None)
        if not callable(method) or name.startswith(("set_", "add_", "remove_", "rename_")):
            continue
        try:
            calls[name] = _safe(method())
        except Exception as exc:
            calls[name] = {"error": str(exc)}

    report = {
        "schemaVersion": 1,
        "iteration": "v710",
        "status": "read-only-curve-payload-inspection",
        "animation": ANIMATION_PATH,
        "modelClass": model.get_class().get_name(),
        "curveRelatedMethods": methods,
        "properties": properties,
        "zeroArgumentCallResults": calls,
        "automaticApproval": False,
        "humanApproved": False,
        "productionReady": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.log("URURU_ANIMATION_CURVES_V710=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


inspect_ururu_animation_curves_v710()
