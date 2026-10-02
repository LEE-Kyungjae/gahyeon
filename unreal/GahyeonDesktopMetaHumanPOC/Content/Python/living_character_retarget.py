"""Reusable fail-closed UE 5.8 IK retarget builder for living-character donors."""

from dataclasses import dataclass
import json
from pathlib import Path

import unreal


@dataclass(frozen=True)
class LivingCharacterRetargetConfig:
    iteration: str
    source_mesh_path: str
    source_animation_path: str
    target_mesh_path: str
    asset_root: str
    source_rig_name: str
    target_rig_name: str
    retargeter_name: str
    animation_root: str
    source_root_bone: str
    target_root_bone: str
    source_chains: tuple
    target_chains: tuple
    search: str
    replace: str
    suffix: str
    report_path: Path
    auto_align_target: bool = False


def _require_asset(path):
    asset = unreal.load_asset(path)
    if asset is None:
        raise RuntimeError(f"required asset unavailable: {path}")
    return asset


def _refuse_existing(path):
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        raise RuntimeError(f"refusing to overwrite immutable asset: {path}")


def _add_chain(controller, name, start, end):
    result = controller.add_retarget_chain(name, start, end, "")
    if str(result) != name:
        raise RuntimeError(f"failed chain {name}: {start}->{end}, got {result}")


def _create_ik_rig(path, mesh, root_bone, chains):
    root, name = path.rsplit("/", 1)
    rig = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        name, root, unreal.IKRigDefinition, unreal.IKRigDefinitionFactory()
    )
    if rig is None:
        raise RuntimeError(f"failed to create IK rig: {path}")
    controller = unreal.IKRigController.get_controller(rig)
    if not controller.set_skeletal_mesh(mesh):
        raise RuntimeError(f"failed to set preview mesh: {path}")
    if not controller.set_retarget_root(root_bone):
        raise RuntimeError(f"failed to set retarget root {root_bone}: {path}")
    for chain in chains:
        _add_chain(controller, *chain)
    if not unreal.EditorAssetLibrary.save_loaded_asset(rig, only_if_is_dirty=False):
        raise RuntimeError(f"failed to save IK rig: {path}")
    return rig


def build_living_character_retarget(config):
    source_rig_path = f"{config.asset_root}/{config.source_rig_name}"
    target_rig_path = f"{config.asset_root}/{config.target_rig_name}"
    retargeter_path = f"{config.asset_root}/{config.retargeter_name}"
    for path in (source_rig_path, target_rig_path, retargeter_path):
        _refuse_existing(path)
    if config.report_path.exists():
        raise RuntimeError(f"refusing to overwrite report: {config.report_path}")
    if unreal.EditorAssetLibrary.does_directory_exist(config.animation_root):
        existing = unreal.EditorAssetLibrary.list_assets(config.animation_root, recursive=True)
        if existing:
            raise RuntimeError(f"refusing to overwrite animations: {existing}")

    source_mesh = _require_asset(config.source_mesh_path)
    source_animation = _require_asset(config.source_animation_path)
    target_mesh = _require_asset(config.target_mesh_path)
    source_rig = _create_ik_rig(
        source_rig_path, source_mesh, config.source_root_bone, config.source_chains
    )
    target_rig = _create_ik_rig(
        target_rig_path, target_mesh, config.target_root_bone, config.target_chains
    )
    retargeter = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        config.retargeter_name,
        config.asset_root,
        unreal.IKRetargeter,
        unreal.IKRetargetFactory(),
    )
    if retargeter is None:
        raise RuntimeError(f"failed to create retargeter: {retargeter_path}")
    controller = unreal.IKRetargeterController.get_controller(retargeter)
    controller.set_ik_rig(unreal.RetargetSourceOrTarget.SOURCE, source_rig)
    controller.set_ik_rig(unreal.RetargetSourceOrTarget.TARGET, target_rig)
    controller.set_preview_mesh(unreal.RetargetSourceOrTarget.SOURCE, source_mesh)
    controller.set_preview_mesh(unreal.RetargetSourceOrTarget.TARGET, target_mesh)
    controller.add_default_ops()
    source_names = {name for name, _, _ in config.source_chains}
    target_names = {name for name, _, _ in config.target_chains}
    if source_names != target_names:
        raise RuntimeError(
            f"source/target chain names differ: {sorted(source_names)} != {sorted(target_names)}"
        )
    mapping_results = {
        name: controller.set_source_chain(name, name) for name in sorted(target_names)
    }
    failed = sorted(name for name, value in mapping_results.items() if not value)
    if failed:
        raise RuntimeError(f"failed chain mappings: {failed}")
    target_pose = None
    if config.auto_align_target:
        target_pose = str(controller.create_retarget_pose(
            f"AutoAlignedTarget_{config.iteration}",
            unreal.RetargetSourceOrTarget.TARGET,
        ))
        if not target_pose or target_pose.lower() == "none":
            raise RuntimeError("failed to create target auto-alignment retarget pose")
        if not controller.set_current_retarget_pose(
            target_pose, unreal.RetargetSourceOrTarget.TARGET
        ):
            raise RuntimeError(f"failed to select target retarget pose: {target_pose}")
        controller.auto_align_all_bones(
            unreal.RetargetSourceOrTarget.TARGET,
            unreal.RetargetAutoAlignMethod.CHAIN_TO_CHAIN,
        )
    if not unreal.EditorAssetLibrary.save_loaded_asset(retargeter, only_if_is_dirty=False):
        raise RuntimeError(f"failed to save retargeter: {retargeter_path}")

    source_data = unreal.EditorAssetLibrary.find_asset_data(config.source_animation_path)
    if not source_data.is_valid():
        raise RuntimeError(f"invalid source animation data: {config.source_animation_path}")
    inputs = unreal.IKRetargetBatchOperationInputs()
    inputs.set_editor_property("assets_to_retarget", [source_data])
    inputs.set_editor_property("source_mesh", source_mesh)
    inputs.set_editor_property("target_mesh", target_mesh)
    inputs.set_editor_property("ik_retarget_asset", retargeter)
    inputs.set_editor_property("search", config.search)
    inputs.set_editor_property("replace", config.replace)
    inputs.set_editor_property("suffix", config.suffix)
    inputs.set_editor_property("target_path", config.animation_root)
    inputs.set_editor_property("use_source_path", False)
    inputs.set_editor_property("include_referenced_assets", False)
    inputs.set_editor_property("overwrite_existing_files", False)
    created = unreal.IKRetargetBatchOperation.run_batch_retarget(inputs)
    if len(created) != 1:
        raise RuntimeError(f"expected one retargeted animation, got {len(created)}")
    created_path = str(created[0].package_name)
    if not unreal.EditorAssetLibrary.save_loaded_asset(
        _require_asset(created_path), only_if_is_dirty=False
    ):
        raise RuntimeError(f"failed to save animation: {created_path}")
    report = {
        "schemaVersion": 1,
        "iteration": config.iteration,
        "status": "draft-retarget-created-visual-validation-required",
        "sourceMesh": config.source_mesh_path,
        "sourceAnimation": config.source_animation_path,
        "targetMesh": config.target_mesh_path,
        "sourceRig": source_rig_path,
        "targetRig": target_rig_path,
        "retargeter": retargeter_path,
        "sourceChains": config.source_chains,
        "targetChains": config.target_chains,
        "targetRetargetPose": target_pose,
        "targetAutoAligned": config.auto_align_target,
        "createdAnimation": created_path,
        "deliberatelyUnmapped": ["facial bones", "muscle/twist helper branches"],
        "visualValidationPending": True,
        "humanApproved": False,
        "releaseEligible": False,
    }
    config.report_path.parent.mkdir(parents=True, exist_ok=False)
    config.report_path.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("LIVING_CHARACTER_RETARGET=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()
    return report
