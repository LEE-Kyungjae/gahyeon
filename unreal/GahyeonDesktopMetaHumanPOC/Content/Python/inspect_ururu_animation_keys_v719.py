"""Extract the actual UE 5.8 names and keys from v708 facial float curves."""

from __future__ import annotations

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
ANIMATION_PATH = "/Game/LivingCharacterPOC/v708/Animation/UruruFace/Ururu_HeadMorphs_Centimeter_v688"
REPORT = ROOT / "artifacts/living-character-poc-v719-ururu-animation-keys/report.json"


def inspect_ururu_animation_keys_v719() -> None:
    if REPORT.exists():
        raise RuntimeError("refusing to overwrite immutable v719 report")
    animation = unreal.load_asset(ANIMATION_PATH)
    if not isinstance(animation, unreal.AnimSequence):
        raise RuntimeError("v708 AnimSequence is unavailable")
    names = [
        str(name)
        for name in unreal.AnimationLibrary.get_animation_curve_names(
            animation, unreal.RawCurveTrackTypes.RCT_FLOAT
        )
    ]
    curves = []
    for name in names:
        times, values = unreal.AnimationLibrary.get_float_keys(animation, name)
        pairs = [{"time": float(time), "value": float(value)} for time, value in zip(times, values)]
        curves.append({
            "name": name,
            "keyCount": len(pairs),
            "nonZeroKeys": [pair for pair in pairs if abs(pair["value"]) > 1e-6],
            "firstKeys": pairs[:12],
        })
    report = {
        "schemaVersion": 1,
        "iteration": "v719",
        "status": "read-only-animation-curve-key-inspection",
        "animation": ANIMATION_PATH,
        "playLengthSeconds": float(animation.get_play_length()),
        "curveNames": names,
        "curves": curves,
        "automaticApproval": False,
        "humanApproved": False,
        "productionReady": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.log("URURU_ANIMATION_KEYS_V719=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


inspect_ururu_animation_keys_v719()
