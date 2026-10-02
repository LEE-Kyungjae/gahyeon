"""Build official UE IK Rig assets and retarget Hayley's walk to Stella/Lily."""

from __future__ import annotations

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
ITERATION = "v561"
DESTINATION = f"/Game/LivingCharacterPOC/{ITERATION}/Retarget"
ANIMATION_DESTINATION = f"/Game/LivingCharacterPOC/{ITERATION}/Animation"
REPORT = ROOT / f"artifacts/living-character-poc-{ITERATION}-hayley-to-stella-ik-walk/report.json"
SOURCE_MESH_PATH = "/Game/LivingCharacterPOC/v448/Characters/HayleyBindClean/Hayley_BindPoseClean_v447"
TARGET_MESH_PATH = "/Game/LivingCharacterPOC/v558/Characters/StellaLilyTextured/StellaLily_PreviewReady_v556"
SOURCE_ANIMATION_PATH = "/Game/LivingCharacterPOC/v459/Animation/AS_HayleyClean_Walk_v459"
TARGET_NAME = "StellaLily"
OUTPUT_ANIMATION_STEM = "AS_StellaLily_IKWalk"

SOURCE_BONES = {
    "root": "root",
    "pelvis": "pelvis",
    "spineLower": "spine",
    "spineUpper": "chest",
    "neck": "neck",
    "head": "head",
    "clavicleL": "lScapula",
    "upperArmL": "lShoulder",
    "handL": "lHand",
    "clavicleR": "rScapula",
    "upperArmR": "rShoulder",
    "handR": "rHand",
    "thighL": "lThigh",
    "footL": "lFoot",
    "toeL": "lToe",
    "thighR": "rThigh",
    "footR": "rFoot",
    "toeR": "rToe",
}

TARGET_BONES = {
    "root": "Bip001",
    "pelvis": "Bip001-Pelvis",
    "spineLower": "Bip001-Spine",
    "spineUpper": "Bip001-Spine2",
    "neck": "Bip001-Neck",
    "head": "Bip001-Head",
    "clavicleL": "Bip001-L-Clavicle",
    "upperArmL": "Bip001-L-UpperArm",
    "handL": "Bip001-L-Hand",
    "clavicleR": "Bip001-R-Clavicle",
    "upperArmR": "Bip001-R-UpperArm",
    "handR": "Bip001-R-Hand",
    "thighL": "Bip001-L-Thigh",
    "footL": "Bip001-L-Foot",
    "toeL": "Bip001-L-Toe0",
    "thighR": "Bip001-R-Thigh",
    "footR": "Bip001-R-Foot",
    "toeR": "Bip001-R-Toe0",
}

CHAINS = (
    ("Root", "root", "root", None),
    ("Spine", "spineLower", "spineUpper", None),
    ("Neck", "neck", "neck", None),
    ("Head", "head", "head", None),
    ("LeftClavicle", "clavicleL", "clavicleL", None),
    ("LeftArm", "upperArmL", "handL", None),
    ("RightClavicle", "clavicleR", "clavicleR", None),
    ("RightArm", "upperArmR", "handR", None),
    ("LeftLeg", "thighL", "footL", "foot_l_goal"),
    ("LeftToe", "toeL", "toeL", None),
    ("RightLeg", "thighR", "footR", "foot_r_goal"),
    ("RightToe", "toeR", "toeR", None),
)


def require_asset(asset_path: str):
    asset = unreal.load_asset(asset_path)
    if asset is None:
        raise RuntimeError(f"missing required asset: {asset_path}")
    return asset


def build_ik_rig(name: str, mesh, bones: dict[str, str]):
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    rig = tools.create_asset(name, DESTINATION, unreal.IKRigDefinition, unreal.IKRigDefinitionFactory())
    if rig is None:
        raise RuntimeError(f"failed to create IK Rig: {name}")
    controller = unreal.IKRigController.get_controller(rig)
    controller.set_skeletal_mesh(mesh)
    controller.set_retarget_root(bones["pelvis"])
    for goal_name, role in (("foot_l_goal", "footL"), ("foot_r_goal", "footR")):
        controller.add_new_goal(goal_name, bones[role])
    for chain_name, start_role, end_role, goal_name in CHAINS:
        controller.add_retarget_chain(
            chain_name,
            bones[start_role],
            bones[end_role],
            goal_name or "",
        )
    for goal_name, thigh_role in (("foot_l_goal", "thighL"), ("foot_r_goal", "thighR")):
        solver_index = controller.add_solver("/Script/IKRig.IKRigLimbSolver")
        controller.set_root_bone(bones[thigh_role], solver_index)
        controller.connect_goal_to_solver(goal_name, solver_index)
    unreal.EditorAssetLibrary.save_loaded_asset(rig, only_if_is_dirty=False)
    return rig, controller


def build_hayley_to_stella_walk_v561() -> dict[str, object]:
    if REPORT.exists() or unreal.EditorAssetLibrary.list_assets(DESTINATION, recursive=True):
        raise RuntimeError("refusing to overwrite immutable v561 outputs")
    source_mesh = require_asset(SOURCE_MESH_PATH)
    target_mesh = require_asset(TARGET_MESH_PATH)
    source_animation = require_asset(SOURCE_ANIMATION_PATH)

    source_rig, source_controller = build_ik_rig(f"IK_Hayley_{ITERATION}", source_mesh, SOURCE_BONES)
    target_rig, target_controller = build_ik_rig(f"IK_{TARGET_NAME}_{ITERATION}", target_mesh, TARGET_BONES)
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    retargeter = tools.create_asset(
        f"RTG_Hayley_{TARGET_NAME}_{ITERATION}",
        DESTINATION,
        unreal.IKRetargeter,
        unreal.IKRetargetFactory(),
    )
    if retargeter is None:
        raise RuntimeError("failed to create IK Retargeter")
    controller = unreal.IKRetargeterController.get_controller(retargeter)
    controller.set_ik_rig(unreal.RetargetSourceOrTarget.SOURCE, source_rig)
    controller.set_ik_rig(unreal.RetargetSourceOrTarget.TARGET, target_rig)
    controller.set_preview_mesh(unreal.RetargetSourceOrTarget.SOURCE, source_mesh)
    controller.set_preview_mesh(unreal.RetargetSourceOrTarget.TARGET, target_mesh)
    controller.add_default_ops()
    for chain_name, *_ in CHAINS:
        if not controller.set_source_chain(chain_name, chain_name):
            raise RuntimeError(f"failed to map retarget chain: {chain_name}")
    controller.create_retarget_pose("AutoAlignedTarget", unreal.RetargetSourceOrTarget.TARGET)
    controller.set_current_retarget_pose("AutoAlignedTarget", unreal.RetargetSourceOrTarget.TARGET)
    controller.auto_align_all_bones(unreal.RetargetSourceOrTarget.TARGET)
    unreal.EditorAssetLibrary.save_loaded_asset(retargeter, only_if_is_dirty=False)

    asset_subsystem = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
    source_data = asset_subsystem.find_asset_data(SOURCE_ANIMATION_PATH)
    generated = unreal.IKRetargetBatchOperation.duplicate_and_retarget(
        [source_data],
        source_mesh,
        target_mesh,
        retargeter,
        search="AS_HayleyClean_Walk_v459",
        replace=f"{OUTPUT_ANIMATION_STEM}_{ITERATION}",
        prefix="",
        suffix="",
    )
    generated_paths = []
    for asset in generated:
        if isinstance(asset, unreal.AssetData):
            old_path = str(asset.package_name)
            asset_name = str(asset.asset_name)
        else:
            old_path = asset.get_path_name().split(".", 1)[0]
            asset_name = asset.get_name()
        new_path = f"{ANIMATION_DESTINATION}/{asset_name}"
        if not unreal.EditorAssetLibrary.rename_asset(old_path, new_path):
            raise RuntimeError(f"failed to move retargeted animation: {old_path} -> {new_path}")
        generated_paths.append(new_path)
    if len(generated_paths) != 1:
        raise RuntimeError(f"expected one retargeted walk, got {generated_paths}")
    unreal.EditorAssetLibrary.save_directory(
        f"/Game/LivingCharacterPOC/{ITERATION}", only_if_is_dirty=False, recursive=True
    )

    report = {
        "schemaVersion": 1,
        "iteration": ITERATION,
        "status": "draft-official-ik-retarget-walk-generated",
        "sourceMesh": SOURCE_MESH_PATH,
        "targetMesh": TARGET_MESH_PATH,
        "sourceAnimation": SOURCE_ANIMATION_PATH,
        "sourceIkRig": source_rig.get_path_name().split(".", 1)[0],
        "targetIkRig": target_rig.get_path_name().split(".", 1)[0],
        "retargeter": retargeter.get_path_name().split(".", 1)[0],
        "retargetedAnimations": generated_paths,
        "chainCount": len(CHAINS),
        "sourceSolverCount": source_controller.get_num_solvers(),
        "targetSolverCount": target_controller.get_num_solvers(),
        "footGoals": ["foot_l_goal", "foot_r_goal"],
        "hypothesis": "UE's official IK Rig and Retargeter with per-leg limb solvers will preserve Stella/Lily foot contact better than direct cross-skeleton bone rotation copying.",
        "visualValidationPending": True,
        "humanApproved": False,
        "releaseEligible": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.log("HAYLEY_TO_STELLA_IK_WALK=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()
    return report


if __name__ == "__main__":
    REPORT_VALUE = build_hayley_to_stella_walk_v561()
