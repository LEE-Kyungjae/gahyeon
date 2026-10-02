"""Build a six-way Ururu neck retarget-pose sweep without touching v586."""

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE_RETARGETER = "/Game/LivingCharacterPOC/v586/Retarget/RTG_Hayley_Ururu_v586"
SOURCE_MESH = "/Game/LivingCharacterPOC/v448/Characters/HayleyBindClean/Hayley_BindPoseClean_v447"
TARGET_MESH = "/Game/LivingCharacterPOC/v585/Characters/UruruCentimeterNormalized/Ururu_CentimeterNormalized_v584"
SOURCE_ANIMATION = "/Game/LivingCharacterPOC/v466/Animation/AS_HayleyClean_CyberIdle_v466"
OUTPUT_ROOT = "/Game/LivingCharacterPOC/v596"
REPORT = ROOT / "artifacts/living-character-poc-v596-ururu-neck-axis-sweep/report.json"
NECK = "ValveBiped_Bip01_Neck1"
CANDIDATES = {
    "pitch_pos12": unreal.Rotator(12.0, 0.0, 0.0),
    "pitch_neg12": unreal.Rotator(-12.0, 0.0, 0.0),
    "yaw_pos12": unreal.Rotator(0.0, 12.0, 0.0),
    "yaw_neg12": unreal.Rotator(0.0, -12.0, 0.0),
    "roll_pos12": unreal.Rotator(0.0, 0.0, 12.0),
    "roll_neg12": unreal.Rotator(0.0, 0.0, -12.0),
}


def require_asset(path):
    asset = unreal.load_asset(path)
    if asset is None:
        raise RuntimeError(f"missing required asset: {path}")
    return asset


def build_ururu_neck_axis_sweep_v596():
    if REPORT.exists() or unreal.EditorAssetLibrary.list_assets(OUTPUT_ROOT, recursive=True):
        raise RuntimeError("refusing to overwrite immutable v596 outputs")
    source_mesh = require_asset(SOURCE_MESH)
    target_mesh = require_asset(TARGET_MESH)
    source_data = unreal.EditorAssetLibrary.find_asset_data(SOURCE_ANIMATION)
    if not source_data.is_valid():
        raise RuntimeError(f"missing source animation: {SOURCE_ANIMATION}")
    records = []
    for label, rotation in CANDIDATES.items():
        retargeter_path = f"{OUTPUT_ROOT}/Retarget/RTG_Ururu_Neck_{label}_v596"
        if not unreal.EditorAssetLibrary.duplicate_asset(SOURCE_RETARGETER, retargeter_path):
            raise RuntimeError(f"failed to duplicate retargeter: {retargeter_path}")
        retargeter = require_asset(retargeter_path)
        controller = unreal.IKRetargeterController.get_controller(retargeter)
        controller.set_rotation_offset_for_retarget_pose_bone(
            NECK, rotation.quaternion(), unreal.RetargetSourceOrTarget.TARGET
        )
        verified = controller.get_rotation_offset_for_retarget_pose_bone(
            NECK, unreal.RetargetSourceOrTarget.TARGET
        )
        unreal.EditorAssetLibrary.save_loaded_asset(retargeter, only_if_is_dirty=False)
        generated = unreal.IKRetargetBatchOperation.duplicate_and_retarget(
            [source_data], source_mesh, target_mesh, retargeter,
            search="AS_HayleyClean_CyberIdle",
            replace=f"AS_Ururu_Neck_{label}",
            prefix="",
            suffix="_v596",
        )
        if len(generated) != 1:
            raise RuntimeError(f"{label}: expected one animation, got {len(generated)}")
        item = generated[0]
        old_path = str(item.package_name) if isinstance(item, unreal.AssetData) else item.get_path_name().split(".", 1)[0]
        asset_name = str(item.asset_name) if isinstance(item, unreal.AssetData) else item.get_name()
        animation_path = f"{OUTPUT_ROOT}/Animation/{asset_name}"
        if not unreal.EditorAssetLibrary.rename_asset(old_path, animation_path):
            raise RuntimeError(f"failed to move {old_path} -> {animation_path}")
        records.append({
            "label": label,
            "retargeter": retargeter_path,
            "animation": animation_path,
            "requestedRotatorDegrees": {"pitch": rotation.pitch, "yaw": rotation.yaw, "roll": rotation.roll},
            "verifiedQuaternion": {key: getattr(verified, key) for key in ("x", "y", "z", "w")},
        })
    unreal.EditorAssetLibrary.save_directory(OUTPUT_ROOT, only_if_is_dirty=False, recursive=True)
    report = {
        "schemaVersion": 1,
        "iteration": "v596",
        "status": "draft-six-way-neck-axis-sweep-generated",
        "hypothesis": "One local neck axis and sign counteracts Ururu's persistent downward retarget bias.",
        "sourceRetargeter": SOURCE_RETARGETER,
        "sourceAnimation": SOURCE_ANIMATION,
        "targetMesh": TARGET_MESH,
        "candidates": records,
        "visualValidationPending": True,
        "humanApproved": False,
        "releaseEligible": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.log("URURU_NECK_AXIS_SWEEP_V596=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


build_ururu_neck_axis_sweep_v596()
