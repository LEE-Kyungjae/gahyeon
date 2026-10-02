"""Batch-retarget Hayley's validated nine-motion library to Stella and Ururu."""

from __future__ import annotations

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
ITERATION = "v588"
SOURCE_MESH = "/Game/LivingCharacterPOC/v448/Characters/HayleyBindClean/Hayley_BindPoseClean_v447"
SOURCE_MOTIONS = {
    "activeIdle": "/Game/LivingCharacterPOC/v466/Animation/AS_HayleyClean_CyberIdle_v466",
    "walk": "/Game/LivingCharacterPOC/v459/Animation/AS_HayleyClean_Walk_v459",
    "run": "/Game/LivingCharacterPOC/v462/Animation/AS_HayleyClean_RunLower_v462",
    "standSit": "/Game/LivingCharacterPOC/v452/Animation/AS_HayleyClean_StandSit_v452",
    "explain": "/Game/LivingCharacterPOC/v451/Animation/AS_HayleyClean_HandsForward_v451",
    "narration": "/Game/LivingCharacterPOC/v472/Animation/AS_HayleyClean_Narration_v472",
    "subtleReaction": "/Game/LivingCharacterPOC/v484/Animation/subtle/AS_HayleyClean_ButWait_subtle_v484",
    "present": "/Game/LivingCharacterPOC/v484/Animation/present/AS_HayleyClean_ButWait_present_v484",
    "emphasis": "/Game/LivingCharacterPOC/v484/Animation/emphasis/AS_HayleyClean_ButWait_emphasis_v484",
}
TARGETS = {
    "stella": {
        "mesh": "/Game/LivingCharacterPOC/v572/Characters/StellaCentimeterNormalized/StellaLily_CentimeterNormalized_v571",
        "retargeter": "/Game/LivingCharacterPOC/v577/Retarget/RTG_Hayley_StellaLily_v577",
        "replace": "AS_Stella_",
        "destination": "/Game/LivingCharacterPOC/v588/Animation/Stella",
    },
    "ururu": {
        "mesh": "/Game/LivingCharacterPOC/v585/Characters/UruruCentimeterNormalized/Ururu_CentimeterNormalized_v584",
        "retargeter": "/Game/LivingCharacterPOC/v586/Retarget/RTG_Hayley_Ururu_v586",
        "replace": "AS_Ururu_",
        "destination": "/Game/LivingCharacterPOC/v588/Animation/Ururu",
    },
}
REPORT = ROOT / "artifacts/living-character-poc-v588-target-motion-libraries/report.json"


def require_asset(path: str):
    asset = unreal.load_asset(path)
    if asset is None:
        raise RuntimeError(f"missing required asset: {path}")
    return asset


def generated_asset_path(asset) -> tuple[str, str]:
    if isinstance(asset, unreal.AssetData):
        return str(asset.package_name), str(asset.asset_name)
    return asset.get_path_name().split(".", 1)[0], asset.get_name()


def build_target_motion_libraries_v588() -> dict[str, object]:
    if REPORT.exists() or unreal.EditorAssetLibrary.list_assets(
        "/Game/LivingCharacterPOC/v588", recursive=True
    ):
        raise RuntimeError("refusing to overwrite immutable v588 outputs")
    source_mesh = require_asset(SOURCE_MESH)
    subsystem = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
    source_data = []
    for motion_id, path in SOURCE_MOTIONS.items():
        data = subsystem.find_asset_data(path)
        if not data.is_valid():
            raise RuntimeError(f"missing source motion: {motion_id}={path}")
        source_data.append(data)

    target_reports = {}
    for target_id, config in TARGETS.items():
        target_mesh = require_asset(config["mesh"])
        retargeter = require_asset(config["retargeter"])
        generated = unreal.IKRetargetBatchOperation.duplicate_and_retarget(
            source_data,
            source_mesh,
            target_mesh,
            retargeter,
            search="AS_HayleyClean_",
            replace=config["replace"],
            prefix="",
            suffix=f"_{ITERATION}",
        )
        moved = []
        for asset in generated:
            old_path, asset_name = generated_asset_path(asset)
            new_path = f"{config['destination']}/{asset_name}"
            if not unreal.EditorAssetLibrary.rename_asset(old_path, new_path):
                raise RuntimeError(f"failed to move {target_id} motion: {old_path} -> {new_path}")
            moved.append(new_path)
        if len(moved) != len(SOURCE_MOTIONS):
            raise RuntimeError(
                f"{target_id} expected {len(SOURCE_MOTIONS)} motions, got {len(moved)}: {moved}"
            )
        target_reports[target_id] = {
            "mesh": config["mesh"],
            "retargeter": config["retargeter"],
            "motions": sorted(moved),
        }
    unreal.EditorAssetLibrary.save_directory(
        "/Game/LivingCharacterPOC/v588", only_if_is_dirty=False, recursive=True
    )
    report = {
        "schemaVersion": 1,
        "iteration": ITERATION,
        "status": "draft-two-character-nine-motion-libraries-generated",
        "sourceMesh": SOURCE_MESH,
        "sourceMotions": SOURCE_MOTIONS,
        "targets": target_reports,
        "motionCountPerTarget": len(SOURCE_MOTIONS),
        "totalGeneratedMotionCount": sum(len(value["motions"]) for value in target_reports.values()),
        "visualValidationPending": True,
        "humanApproved": False,
        "releaseEligible": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.log("TARGET_MOTION_LIBRARIES=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()
    return report


REPORT_VALUE = build_target_motion_libraries_v588()
