"""Validate the immutable v693 legacy-FBX Ururu facial import."""

from __future__ import annotations

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
MESH_PATH = "/Game/LivingCharacterPOC/v693/Characters/UruruFacial/Ururu_StaticHeadMorphs_v691"
SKELETON_PATH = "/Game/LivingCharacterPOC/v585/Characters/UruruCentimeterNormalized/Ururu_CentimeterNormalized_v584_Skeleton"
REPORT = ROOT / "artifacts/living-character-poc-v694-ururu-legacy-head-morph-validation/report.json"
REQUIRED = {"EyeBlink_L", "EyeBlink_R", "GazeLeft", "GazeRight"}


def validate_ururu_legacy_head_morphs_v694() -> dict[str, object]:
    if REPORT.exists():
        raise RuntimeError("refusing to overwrite immutable v694 report")
    mesh = unreal.load_asset(MESH_PATH)
    skeleton = unreal.load_asset(SKELETON_PATH)
    if not isinstance(mesh, unreal.SkeletalMesh):
        raise RuntimeError(f"missing v693 skeletal mesh: {MESH_PATH}")
    if skeleton is None:
        raise RuntimeError(f"missing validated skeleton: {SKELETON_PATH}")
    actual_skeleton = mesh.get_editor_property("skeleton")
    if actual_skeleton != skeleton:
        raise RuntimeError(
            f"v693 skeleton mismatch: expected={SKELETON_PATH}, "
            f"actual={actual_skeleton.get_path_name() if actual_skeleton else None}"
        )
    morphs = sorted(str(name) for name in mesh.get_all_morph_target_names())
    missing = sorted(REQUIRED - set(morphs))
    if missing:
        raise RuntimeError(f"v693 lost required morph targets: {missing}; actual={morphs}")
    animations = sorted(
        path for path in unreal.EditorAssetLibrary.list_assets("/Game/LivingCharacterPOC/v693", recursive=True)
        if isinstance(unreal.load_asset(path), unreal.AnimSequence)
    )
    if animations:
        raise RuntimeError(f"animation-free FBX unexpectedly produced animations: {animations}")
    report = {
        "schemaVersion": 1,
        "iteration": "v694",
        "status": "validated-legacy-fbx-facial-morph-import",
        "sourceIteration": "v693",
        "skeletalMesh": MESH_PATH,
        "skeleton": SKELETON_PATH,
        "skeletonReused": True,
        "morphTargets": morphs,
        "requiredMorphTargets": sorted(REQUIRED),
        "unexpectedAnimations": animations,
        "importer": "legacy-fbx",
        "visualValidationPending": True,
        "automaticApproval": False,
        "humanApproved": False,
        "productionReady": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.log("URURU_LEGACY_HEAD_MORPH_VALIDATION_V694=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()
    return report


REPORT_VALUE = validate_ururu_legacy_head_morphs_v694()
