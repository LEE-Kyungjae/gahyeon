"""Retarget the standard Mixamo Gynoid walk onto Hayley's primary body chains."""

import json
from pathlib import Path

import unreal


SOURCE_MESH = "/Game/LivingCharacterPOC/v371/Donors/GynoidWalk/FemBot_1000"
SOURCE_ANIMATION = "/Game/LivingCharacterPOC/v371/Donors/GynoidWalk/FemBot_1000_Anim"
TARGET_MESH = "/Game/LivingCharacterPOC/v371/Characters/Hayley/Hayley2"
RIG_ROOT = "/Game/LivingCharacterPOC/v380/Retarget"
SOURCE_RIG = f"{RIG_ROOT}/IK_GynoidMixamo_Source_v380"
TARGET_RIG = f"{RIG_ROOT}/IK_Hayley_Target_v380"
RETARGETER = f"{RIG_ROOT}/RTG_GynoidWalkToHayley_v380"
ANIMATION_ROOT = "/Game/LivingCharacterPOC/v380/Animation"
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v380-gynoid-walk-retarget/report.json"
)


SOURCE_CHAINS = (
    ("Spine", "mixamorig:Hips", "mixamorig:Neck"),
    ("Head", "mixamorig:Neck", "mixamorig:Head"),
    ("LeftClavicle", "mixamorig:LeftShoulder", "mixamorig:LeftShoulder"),
    ("LeftArm", "mixamorig:LeftArm", "mixamorig:LeftHand"),
    ("RightClavicle", "mixamorig:RightShoulder", "mixamorig:RightShoulder"),
    ("RightArm", "mixamorig:RightArm", "mixamorig:RightHand"),
    ("LeftLeg", "mixamorig:LeftUpLeg", "mixamorig:LeftFoot"),
    ("LeftFoot", "mixamorig:LeftFoot", "mixamorig:LeftToeBase"),
    ("RightLeg", "mixamorig:RightUpLeg", "mixamorig:RightFoot"),
    ("RightFoot", "mixamorig:RightFoot", "mixamorig:RightToeBase"),
)
TARGET_CHAINS = (
    ("Spine", "pelvis", "neck"),
    ("Head", "neck", "head"),
    ("LeftClavicle", "lScapula", "lScapula"),
    ("LeftArm", "lShoulder", "lHand"),
    ("RightClavicle", "rScapula", "rScapula"),
    ("RightArm", "rShoulder", "rHand"),
    ("LeftLeg", "lThigh", "lFoot"),
    ("LeftFoot", "lFoot", "lToe"),
    ("RightLeg", "rThigh", "rFoot"),
    ("RightFoot", "rFoot", "rToe"),
)


def require_asset_v380(path):
    asset = unreal.load_asset(path)
    if asset is None:
        raise RuntimeError(f"required asset unavailable: {path}")
    return asset


def refuse_existing_v380(path):
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        raise RuntimeError(f"refusing to overwrite immutable asset: {path}")


def create_retarget_chain_v380(controller, name, start, end):
    result = controller.add_retarget_chain(name, start, end, "")
    if str(result) != name:
        raise RuntimeError(f"failed chain {name}: {start}->{end}, got {result}")


def create_ik_rig_v380(asset_path, mesh, root_bone, chains):
    root, name = asset_path.rsplit("/", 1)
    rig = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        name, root, unreal.IKRigDefinition, unreal.IKRigDefinitionFactory()
    )
    if rig is None:
        raise RuntimeError(f"failed to create IK rig: {asset_path}")
    controller = unreal.IKRigController.get_controller(rig)
    if not controller.set_skeletal_mesh(mesh):
        raise RuntimeError(f"failed to set preview mesh: {asset_path}")
    if not controller.set_retarget_root(root_bone):
        raise RuntimeError(f"failed to set retarget root {root_bone}: {asset_path}")
    for chain in chains:
        create_retarget_chain_v380(controller, *chain)
    if not unreal.EditorAssetLibrary.save_loaded_asset(rig, only_if_is_dirty=False):
        raise RuntimeError(f"failed to save IK rig: {asset_path}")
    return rig


def build_hayley_gynoid_walk_retarget_v380():
    for path in (SOURCE_RIG, TARGET_RIG, RETARGETER):
        refuse_existing_v380(path)
    if REPORT.exists():
        raise RuntimeError(f"refusing to overwrite report: {REPORT}")
    if unreal.EditorAssetLibrary.does_directory_exist(ANIMATION_ROOT):
        existing = unreal.EditorAssetLibrary.list_assets(ANIMATION_ROOT, recursive=True)
        if existing:
            raise RuntimeError(f"refusing to overwrite animations: {existing}")
    source_mesh = require_asset_v380(SOURCE_MESH)
    source_animation = require_asset_v380(SOURCE_ANIMATION)
    target_mesh = require_asset_v380(TARGET_MESH)
    source_rig = create_ik_rig_v380(SOURCE_RIG, source_mesh, "mixamorig:Hips", SOURCE_CHAINS)
    target_rig = create_ik_rig_v380(TARGET_RIG, target_mesh, "pelvis", TARGET_CHAINS)

    root, name = RETARGETER.rsplit("/", 1)
    retargeter = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        name, root, unreal.IKRetargeter, unreal.IKRetargetFactory()
    )
    if retargeter is None:
        raise RuntimeError("failed to create Gynoid-to-Hayley retargeter")
    controller = unreal.IKRetargeterController.get_controller(retargeter)
    controller.set_ik_rig(unreal.RetargetSourceOrTarget.SOURCE, source_rig)
    controller.set_ik_rig(unreal.RetargetSourceOrTarget.TARGET, target_rig)
    controller.set_preview_mesh(unreal.RetargetSourceOrTarget.SOURCE, source_mesh)
    controller.set_preview_mesh(unreal.RetargetSourceOrTarget.TARGET, target_mesh)
    controller.add_default_ops()
    mappings = {
        name: controller.set_source_chain(name, name)
        for name, _, _ in TARGET_CHAINS
    }
    failed = sorted(name for name, value in mappings.items() if not value)
    if failed:
        raise RuntimeError(f"failed chain mappings: {failed}")
    if not unreal.EditorAssetLibrary.save_loaded_asset(retargeter, only_if_is_dirty=False):
        raise RuntimeError("failed to save retargeter")

    inputs = unreal.IKRetargetBatchOperationInputs()
    inputs.set_editor_property(
        "assets_to_retarget", [unreal.EditorAssetLibrary.find_asset_data(SOURCE_ANIMATION)]
    )
    inputs.set_editor_property("source_mesh", source_mesh)
    inputs.set_editor_property("target_mesh", target_mesh)
    inputs.set_editor_property("ik_retarget_asset", retargeter)
    inputs.set_editor_property("search", "FemBot_1000_Anim")
    inputs.set_editor_property("replace", "AS_Hayley_GynoidWalk")
    inputs.set_editor_property("suffix", "_v380")
    inputs.set_editor_property("target_path", ANIMATION_ROOT)
    inputs.set_editor_property("use_source_path", False)
    inputs.set_editor_property("include_referenced_assets", False)
    inputs.set_editor_property("overwrite_existing_files", False)
    created = unreal.IKRetargetBatchOperation.run_batch_retarget(inputs)
    if len(created) != 1:
        raise RuntimeError(f"expected one retargeted animation, got {len(created)}")
    created_path = str(created[0].package_name)
    if not unreal.EditorAssetLibrary.save_loaded_asset(
        require_asset_v380(created_path), only_if_is_dirty=False
    ):
        raise RuntimeError(f"failed to save animation: {created_path}")
    report = {
        "schemaVersion": 1,
        "iteration": "v380",
        "status": "draft-retarget-created-visual-validation-required",
        "sourceMesh": SOURCE_MESH,
        "sourceAnimation": SOURCE_ANIMATION,
        "targetMesh": TARGET_MESH,
        "sourceRig": SOURCE_RIG,
        "targetRig": TARGET_RIG,
        "retargeter": RETARGETER,
        "sourceChains": SOURCE_CHAINS,
        "targetChains": TARGET_CHAINS,
        "createdAnimation": created_path,
        "deliberatelyUnmapped": ["Hayley facial bones", "Hayley muscle helper bones"],
        "hypothesis": "Primary humanoid chains transfer the walk without double-driving Hayley's auxiliary deformation branches.",
        "visualValidationPending": True,
        "humanApproved": False,
        "releaseEligible": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("HAYLEY_V380_RETARGET=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


build_hayley_gynoid_walk_retarget_v380()
