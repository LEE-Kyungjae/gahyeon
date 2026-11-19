"""Retarget all nine motions through the visually preferred Ururu head pose."""

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
ITERATION = "v601"
SOURCE_MESH = "/Game/LivingCharacterPOC/v448/Characters/HayleyBindClean/Hayley_BindPoseClean_v447"
TARGET_MESH = "/Game/LivingCharacterPOC/v585/Characters/UruruCentimeterNormalized/Ururu_CentimeterNormalized_v584"
RETARGETER = "/Game/LivingCharacterPOC/v599/Retarget/RTG_Ururu_Head_roll_neg20_v599"
DESTINATION = "/Game/LivingCharacterPOC/v601/Animation/Ururu"
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
REPORT = ROOT / "artifacts/living-character-poc-v601-ururu-corrected-motion-library/report.json"


def require_asset(path):
    asset = unreal.load_asset(path)
    if asset is None:
        raise RuntimeError(f"missing required asset: {path}")
    return asset


def generated_asset_path(asset):
    if isinstance(asset, unreal.AssetData):
        return str(asset.package_name), str(asset.asset_name)
    return asset.get_path_name().split(".", 1)[0], asset.get_name()


def build_ururu_corrected_motion_library_v601():
    if REPORT.exists() or unreal.EditorAssetLibrary.list_assets("/Game/LivingCharacterPOC/v601", recursive=True):
        raise RuntimeError("refusing to overwrite immutable v601 outputs")
    source_mesh = require_asset(SOURCE_MESH)
    target_mesh = require_asset(TARGET_MESH)
    retargeter = require_asset(RETARGETER)
    subsystem = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
    source_data = []
    for motion_id, path in SOURCE_MOTIONS.items():
        data = subsystem.find_asset_data(path)
        if not data.is_valid():
            raise RuntimeError(f"missing source motion: {motion_id}={path}")
        source_data.append(data)
    generated = unreal.IKRetargetBatchOperation.duplicate_and_retarget(
        source_data, source_mesh, target_mesh, retargeter,
        search="AS_HayleyClean_", replace="AS_Ururu_Corrected_",
        prefix="", suffix=f"_{ITERATION}",
    )
    moved = []
    for item in generated:
        old_path, asset_name = generated_asset_path(item)
        new_path = f"{DESTINATION}/{asset_name}"
        if not unreal.EditorAssetLibrary.rename_asset(old_path, new_path):
            raise RuntimeError(f"failed to move {old_path} -> {new_path}")
        moved.append(new_path)
    if len(moved) != len(SOURCE_MOTIONS):
        raise RuntimeError(f"expected {len(SOURCE_MOTIONS)} motions, got {len(moved)}")
    unreal.EditorAssetLibrary.save_directory("/Game/LivingCharacterPOC/v601", only_if_is_dirty=False, recursive=True)
    report = {
        "schemaVersion": 1,
        "iteration": ITERATION,
        "status": "draft-nine-motion-library-with-head-pose-correction",
        "hypothesis": "The v599 head roll -20 degree pose raises Ururu's gaze consistently across every motion family.",
        "targetPoseCandidate": "roll_neg20",
        "retargeter": RETARGETER,
        "sourceMotions": SOURCE_MOTIONS,
        "generatedMotions": sorted(moved),
        "visualValidationPending": True,
        "humanApproved": False,
        "releaseEligible": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.log("URURU_CORRECTED_LIBRARY_V601=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


build_ururu_corrected_motion_library_v601()
