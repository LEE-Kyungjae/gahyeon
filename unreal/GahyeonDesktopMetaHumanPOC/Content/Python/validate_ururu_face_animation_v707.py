"""Validate the v706 Ururu AnimSequence and its imported curve payload."""

from __future__ import annotations

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
ANIMATION = "/Game/LivingCharacterPOC/v706/Animation/UruruFace/Ururu_HeadMorphs_Centimeter_v688"
SKELETON = "/Game/LivingCharacterPOC/v585/Characters/UruruCentimeterNormalized/Ururu_CentimeterNormalized_v584_Skeleton"
REPORT = ROOT / "artifacts/living-character-poc-v707-ururu-face-animation-validation/report.json"


def validate_ururu_face_animation_v707():
    if REPORT.exists():
        raise RuntimeError("refusing to overwrite immutable v707 report")
    animation = unreal.load_asset(ANIMATION)
    skeleton = unreal.load_asset(SKELETON)
    if not isinstance(animation, unreal.AnimSequence):
        raise RuntimeError(f"v706 asset is not an AnimSequence: {animation}")
    if skeleton is None or animation.get_editor_property("skeleton") != skeleton:
        raise RuntimeError("v706 AnimSequence is not bound to the validated skeleton")
    model = animation.get_editor_property("data_model_interface")
    if model is None:
        raise RuntimeError("v706 AnimSequence has no animation data model")
    stats = {}
    for name in (
        "get_number_of_float_curves",
        "get_number_of_frames",
        "get_number_of_keys",
        "get_num_bone_tracks",
        "get_play_length",
    ):
        method = getattr(model, name, None)
        if callable(method):
            stats[name] = method()
    if stats.get("get_number_of_float_curves", 0) < 4:
        raise RuntimeError(f"v706 animation lacks expected morph curves: {stats}")
    report = {
        "schemaVersion": 1,
        "iteration": "v707",
        "status": "validated-draft-ururu-face-animation-payload",
        "animation": ANIMATION,
        "class": animation.get_class().get_name(),
        "skeleton": SKELETON,
        "playLengthSeconds": float(animation.get_play_length()),
        "dataModelStats": stats,
        "visualValidationPending": True,
        "automaticApproval": False,
        "humanApproved": False,
        "productionReady": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.log("URURU_FACE_ANIMATION_VALIDATION_V707=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


validate_ururu_face_animation_v707()
