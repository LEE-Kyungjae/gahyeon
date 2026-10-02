"""Create a Diana target retarget-pose candidate with lowered upper arms."""

import json
from pathlib import Path

import unreal


SOURCE_RETARGETER = (
    "/Game/Gahyeon/Character2/Diana/v039/Retarget/"
    "RTG_GahyeonToDiana_PrimaryLegs_v039"
)
RETARGETER = (
    "/Game/Gahyeon/Character2/Diana/v344/Retarget/"
    "RTG_GahyeonToDiana_APose_v344"
)
SOURCE_MESH = (
    "/Game/Gahyeon/CharacterPipeline/v244/AssembledMedium/"
    "Gahyeon_AnimationPOC_v244/Body/"
    "SKM_MHC_Skotukeda_SweaterJeansHightop_v243_BodyMesh"
)
TARGET_MESH = "/Game/Gahyeon/Character2/Diana/v024/Source/SK_Diana_CM_v024"
SOURCE_ANIMATIONS = (
    "/Game/Gahyeon/CharacterPipeline/v244/Animation/AS_Gahyeon_Idle_v244",
    "/Game/Gahyeon/CharacterPipeline/v244/Animation/AS_Gahyeon_WalkForward_v244",
    "/Game/Gahyeon/CharacterPipeline/v244/Animation/AS_Gahyeon_RunForward_v244",
)
ANIMATION_ROOT = "/Game/Gahyeon/Character2/Diana/v345/Animation"
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v344-diana-apose-retarget-build/report.json"
)


def require_asset(path):
    asset = unreal.load_asset(path)
    if asset is None:
        raise RuntimeError(f"required asset unavailable: {path}")
    return asset


def build_diana_apose_retarget_v344():
    if unreal.EditorAssetLibrary.does_asset_exist(RETARGETER):
        raise RuntimeError(f"refusing to overwrite immutable retargeter: {RETARGETER}")
    if unreal.EditorAssetLibrary.does_directory_exist(ANIMATION_ROOT):
        existing = unreal.EditorAssetLibrary.list_assets(
            ANIMATION_ROOT, recursive=True, include_folder=False
        )
        if existing:
            raise RuntimeError(f"refusing to overwrite animation output: {existing}")
    if not unreal.EditorAssetLibrary.duplicate_asset(SOURCE_RETARGETER, RETARGETER):
        raise RuntimeError("failed to duplicate Diana retargeter")
    retargeter = require_asset(RETARGETER)
    controller = unreal.IKRetargeterController.get_controller(retargeter)
    offsets = {
        "l_upperarm": unreal.Rotator(0.0, 0.0, 35.0),
        "r_upperarm": unreal.Rotator(0.0, 0.0, -35.0),
    }
    verified = {}
    for bone, rotation in offsets.items():
        controller.set_rotation_offset_for_retarget_pose_bone(
            bone, rotation.quaternion(), unreal.RetargetSourceOrTarget.TARGET
        )
        value = controller.get_rotation_offset_for_retarget_pose_bone(
            bone, unreal.RetargetSourceOrTarget.TARGET
        )
        verified[bone] = {
            "x": value.x,
            "y": value.y,
            "z": value.z,
            "w": value.w,
        }
    if not unreal.EditorAssetLibrary.save_loaded_asset(retargeter, only_if_is_dirty=False):
        raise RuntimeError("failed to save A-pose retargeter")
    source_mesh = require_asset(SOURCE_MESH)
    target_mesh = require_asset(TARGET_MESH)
    source_data = [unreal.EditorAssetLibrary.find_asset_data(path) for path in SOURCE_ANIMATIONS]
    if any(not item.is_valid() for item in source_data):
        raise RuntimeError("one or more source animations are unavailable")
    inputs = unreal.IKRetargetBatchOperationInputs()
    inputs.set_editor_property("assets_to_retarget", source_data)
    inputs.set_editor_property("source_mesh", source_mesh)
    inputs.set_editor_property("target_mesh", target_mesh)
    inputs.set_editor_property("ik_retarget_asset", retargeter)
    inputs.set_editor_property("search", "AS_Gahyeon_")
    inputs.set_editor_property("replace", "AS_Diana_")
    inputs.set_editor_property("suffix", "_APose_v345")
    inputs.set_editor_property("target_path", ANIMATION_ROOT)
    inputs.set_editor_property("use_source_path", False)
    inputs.set_editor_property("include_referenced_assets", False)
    inputs.set_editor_property("overwrite_existing_files", False)
    created = unreal.IKRetargetBatchOperation.run_batch_retarget(inputs)
    if len(created) != len(SOURCE_ANIMATIONS):
        raise RuntimeError(f"expected 3 animations, created {len(created)}")
    created_paths = [str(item.package_name) for item in created]
    for path in created_paths:
        if not unreal.EditorAssetLibrary.save_loaded_asset(
            require_asset(path), only_if_is_dirty=False
        ):
            raise RuntimeError(f"failed to save animation: {path}")
    report = {
        "schemaVersion": 1,
        "iterations": ["v344", "v345"],
        "status": "draft-apose-retarget-ready-for-visual-validation",
        "sourceRetargeter": SOURCE_RETARGETER,
        "retargeter": RETARGETER,
        "targetPoseOffsetsDegrees": {"l_upperarmRoll": 35.0, "r_upperarmRoll": -35.0},
        "verifiedQuaternions": verified,
        "createdAnimations": created_paths,
        "hypothesis": (
            "Opposed target upper-arm roll offsets align Diana's T-pose with the "
            "MetaHuman A-pose and lower both arms during idle and locomotion."
        ),
        "visualValidationPending": True,
        "humanApproved": False,
        "productionReady": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("DIANA_V344_APOSE=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


build_diana_apose_retarget_v344()
