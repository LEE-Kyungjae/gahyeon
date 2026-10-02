"""Build Diana locomotion using only the real thigh-shin-foot retarget chains.

The donor skeleton has separate auxiliary thigh/twist branches that deform coat and
muscle geometry.  They are deliberately not mapped as second legs here; driving
both branches from the same source chain caused duplicated deformation during run.
"""

import json
from pathlib import Path

import unreal


SOURCE_RIG_PATH = "/Game/Gahyeon/Character2/Diana/v008/Retarget/IK_Gahyeon_Source_v008"
SOURCE_MESH_PATH = (
    "/Game/Gahyeon/CharacterPipeline/v244/AssembledMedium/"
    "Gahyeon_AnimationPOC_v244/Body/"
    "SKM_MHC_Skotukeda_SweaterJeansHightop_v243_BodyMesh"
)
SOURCE_ANIMATION_PATHS = [
    "/Game/Gahyeon/CharacterPipeline/v244/Animation/AS_Gahyeon_Idle_v244",
    "/Game/Gahyeon/CharacterPipeline/v244/Animation/AS_Gahyeon_WalkForward_v244",
    "/Game/Gahyeon/CharacterPipeline/v244/Animation/AS_Gahyeon_RunForward_v244",
]
TARGET_MESH_PATH = "/Game/Gahyeon/Character2/Diana/v024/Source/SK_Diana_CM_v024"
TARGET_RIG_ROOT = "/Game/Gahyeon/Character2/Diana/v038/Retarget"
TARGET_RIG_NAME = "IK_Diana_PrimaryLegs_v038"
RETARGETER_ROOT = "/Game/Gahyeon/Character2/Diana/v039/Retarget"
RETARGETER_NAME = "RTG_GahyeonToDiana_PrimaryLegs_v039"
ANIMATION_ROOT = "/Game/Gahyeon/Character2/Diana/v040/Animation"
REPORT_PATH = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/"
    "diana-v040-primary-chain-retarget.json"
)


def refuse_existing(path):
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        raise RuntimeError(f"refusing to overwrite immutable asset: {path}")


def require_asset(path):
    asset = unreal.EditorAssetLibrary.load_asset(path)
    if asset is None:
        raise RuntimeError(f"required asset unavailable: {path}")
    return asset


def create_chain(controller, name, start, end):
    created = controller.add_retarget_chain(name, start, end, "")
    if str(created) != name:
        raise RuntimeError(f"failed retarget chain {name}: {start}->{end}, got {created}")


target_rig_path = f"{TARGET_RIG_ROOT}/{TARGET_RIG_NAME}"
retargeter_path = f"{RETARGETER_ROOT}/{RETARGETER_NAME}"
refuse_existing(target_rig_path)
refuse_existing(retargeter_path)
if unreal.EditorAssetLibrary.does_directory_exist(ANIMATION_ROOT):
    existing = unreal.EditorAssetLibrary.list_assets(
        ANIMATION_ROOT, recursive=True, include_folder=False
    )
    if existing:
        raise RuntimeError(f"refusing to overwrite animation output: {existing}")

source_rig = require_asset(SOURCE_RIG_PATH)
source_mesh = require_asset(SOURCE_MESH_PATH)
target_mesh = require_asset(TARGET_MESH_PATH)

target_rig = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
    TARGET_RIG_NAME,
    TARGET_RIG_ROOT,
    unreal.IKRigDefinition,
    unreal.IKRigDefinitionFactory(),
)
if target_rig is None:
    raise RuntimeError("failed to create Diana primary-chain IK Rig")
target_controller = unreal.IKRigController.get_controller(target_rig)
if not target_controller.set_skeletal_mesh(target_mesh):
    raise RuntimeError("failed to assign Diana preview mesh")
if not target_controller.set_retarget_root("hip"):
    raise RuntimeError("failed to set Diana retarget root")
for chain in (
    ("Spine", "spine_0", "neck_0"),
    ("Head", "neck_0", "head_002"),
    ("LeftClavicle", "l_shoulder", "l_shoulder"),
    ("LeftArm", "l_upperarm", "l_hand"),
    ("RightClavicle", "r_shoulder", "r_shoulder"),
    ("RightArm", "r_upperarm", "r_hand"),
    ("LeftLeg", "l_thigh_001", "l_foot"),
    ("LeftFoot", "l_foot", "l_toe"),
    ("RightLeg", "r_thigh_001", "r_foot"),
    ("RightFoot", "r_foot", "r_toe"),
):
    create_chain(target_controller, *chain)
if not unreal.EditorAssetLibrary.save_loaded_asset(target_rig, only_if_is_dirty=False):
    raise RuntimeError("failed to save Diana primary-chain IK Rig")

retargeter = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
    RETARGETER_NAME,
    RETARGETER_ROOT,
    unreal.IKRetargeter,
    unreal.IKRetargetFactory(),
)
if retargeter is None:
    raise RuntimeError("failed to create Diana primary-chain retargeter")
retarget_controller = unreal.IKRetargeterController.get_controller(retargeter)
retarget_controller.set_ik_rig(unreal.RetargetSourceOrTarget.SOURCE, source_rig)
retarget_controller.set_ik_rig(unreal.RetargetSourceOrTarget.TARGET, target_rig)
retarget_controller.set_preview_mesh(unreal.RetargetSourceOrTarget.SOURCE, source_mesh)
retarget_controller.set_preview_mesh(unreal.RetargetSourceOrTarget.TARGET, target_mesh)
retarget_controller.add_default_ops()
chain_map = {
    "Spine": "Spine",
    "Head": "Head",
    "LeftClavicle": "LeftClavicle",
    "LeftArm": "LeftArm",
    "RightClavicle": "RightClavicle",
    "RightArm": "RightArm",
    "LeftLeg": "LeftLeg",
    "LeftFoot": "LeftFoot",
    "RightLeg": "RightLeg",
    "RightFoot": "RightFoot",
}
mapping_results = {
    target: retarget_controller.set_source_chain(source, target)
    for target, source in chain_map.items()
}
failed = sorted(name for name, result in mapping_results.items() if not result)
if failed:
    raise RuntimeError(f"failed primary chain mappings: {failed}")
if not unreal.EditorAssetLibrary.save_loaded_asset(retargeter, only_if_is_dirty=False):
    raise RuntimeError("failed to save Diana primary-chain retargeter")

source_data = [
    unreal.EditorAssetLibrary.find_asset_data(path) for path in SOURCE_ANIMATION_PATHS
]
if any(not data.is_valid() for data in source_data):
    raise RuntimeError("one or more source animations are unavailable")
inputs = unreal.IKRetargetBatchOperationInputs()
inputs.set_editor_property("assets_to_retarget", source_data)
inputs.set_editor_property("source_mesh", source_mesh)
inputs.set_editor_property("target_mesh", target_mesh)
inputs.set_editor_property("ik_retarget_asset", retargeter)
inputs.set_editor_property("search", "AS_Gahyeon_")
inputs.set_editor_property("replace", "AS_Diana_")
inputs.set_editor_property("suffix", "_PrimaryLegs_v040")
inputs.set_editor_property("target_path", ANIMATION_ROOT)
inputs.set_editor_property("use_source_path", False)
inputs.set_editor_property("include_referenced_assets", False)
inputs.set_editor_property("overwrite_existing_files", False)
created = unreal.IKRetargetBatchOperation.run_batch_retarget(inputs)
if len(created) != len(SOURCE_ANIMATION_PATHS):
    raise RuntimeError(f"expected 3 animations, created {len(created)}")
created_paths = [str(data.package_name) for data in created]
for path in created_paths:
    asset = require_asset(path)
    if not unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError(f"failed to save retargeted animation: {path}")

report = {
    "schemaVersion": 1,
    "iteration": "v040",
    "status": "draft-primary-chain-retarget-ready-for-visual-validation",
    "hypothesis": (
        "Mapping only the actual thigh-shin-foot chains avoids double-driving the "
        "separate garment/muscle auxiliary thigh branches."
    ),
    "targetRig": target_rig_path,
    "retargeter": retargeter_path,
    "chainMap": chain_map,
    "deliberatelyUnmapped": ["LeftUpperLegAux", "RightUpperLegAux"],
    "createdAnimations": created_paths,
    "visualValidationPending": True,
    "automaticApproval": False,
}
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n")
unreal.log("DIANA_V040_PRIMARY_CHAIN_READY=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
