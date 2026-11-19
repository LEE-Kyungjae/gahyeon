"""Build Diana locomotion with separate spine, neck, and head retarget chains."""

import json
import math
from pathlib import Path

import unreal


SOURCE_RIG = "/Game/Gahyeon/Character2/Diana/v008/Retarget/IK_Gahyeon_Source_v008"
SOURCE_MESH = (
    "/Game/Gahyeon/CharacterPipeline/v244/AssembledMedium/"
    "Gahyeon_AnimationPOC_v244/Body/"
    "SKM_MHC_Skotukeda_SweaterJeansHightop_v243_BodyMesh"
)
SOURCE_ANIMATIONS = (
    "/Game/Gahyeon/CharacterPipeline/v244/Animation/AS_Gahyeon_Idle_v244",
    "/Game/Gahyeon/CharacterPipeline/v244/Animation/AS_Gahyeon_WalkForward_v244",
    "/Game/Gahyeon/CharacterPipeline/v244/Animation/AS_Gahyeon_RunForward_v244",
)
TARGET_MESH = "/Game/Gahyeon/Character2/Diana/v024/Source/SK_Diana_CM_v024"
TARGET_RIG = "/Game/Gahyeon/Character2/Diana/v370/Retarget/IK_Diana_NeckHead_v370"
RETARGETER = "/Game/Gahyeon/Character2/Diana/v371/Retarget/RTG_GahyeonToDiana_NeckHead_v371"
ANIMATION_ROOT = "/Game/Gahyeon/Character2/Diana/v372/Animation"
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v370-diana-neck-head-retarget/report.json"
)


def require_asset(path):
    asset = unreal.load_asset(path)
    if asset is None:
        raise RuntimeError(f"required asset unavailable: {path}")
    return asset


def refuse_existing(path):
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        raise RuntimeError(f"refusing to overwrite immutable asset: {path}")


def quat_angle(first, other):
    dot = abs(first.x * other.x + first.y * other.y + first.z * other.z + first.w * other.w)
    return math.degrees(2.0 * math.acos(max(-1.0, min(1.0, dot))))


def max_rotation_delta(animation, bone):
    rotations = list(unreal.AnimationLibrary.get_raw_track_rotation_data(animation, bone))
    if not rotations:
        return None
    return round(max(quat_angle(rotations[0], value) for value in rotations), 4)


def build_diana_neck_head_retarget_v370():
    for path in (TARGET_RIG, RETARGETER):
        refuse_existing(path)
    if unreal.EditorAssetLibrary.does_directory_exist(ANIMATION_ROOT):
        existing = unreal.EditorAssetLibrary.list_assets(ANIMATION_ROOT, True, False)
        if existing:
            raise RuntimeError(f"refusing to overwrite animation output: {existing}")

    source_rig = require_asset(SOURCE_RIG)
    source_mesh = require_asset(SOURCE_MESH)
    target_mesh = require_asset(TARGET_MESH)
    modifier = unreal.SkeletonModifier()
    if not modifier.set_skeletal_mesh(target_mesh):
        raise RuntimeError("could not inspect Diana skeleton hierarchy")
    spine_end = str(modifier.get_parent_name("neck_0"))
    neck_end = str(modifier.get_parent_name("head_002"))
    if spine_end.lower() in ("", "none") or neck_end.lower() in ("", "none"):
        raise RuntimeError(f"invalid Diana torso hierarchy: spine={spine_end}, neck={neck_end}")

    rig_root, rig_name = TARGET_RIG.rsplit("/", 1)
    target_rig = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        rig_name, rig_root, unreal.IKRigDefinition, unreal.IKRigDefinitionFactory()
    )
    controller = unreal.IKRigController.get_controller(target_rig)
    controller.set_skeletal_mesh(target_mesh)
    controller.set_retarget_root("hip")
    target_chains = (
        ("Spine", "spine_0", spine_end),
        ("Neck", "neck_0", neck_end),
        ("Head", "head_002", "head_002"),
        ("LeftClavicle", "l_shoulder", "l_shoulder"),
        ("LeftArm", "l_upperarm", "l_hand"),
        ("RightClavicle", "r_shoulder", "r_shoulder"),
        ("RightArm", "r_upperarm", "r_hand"),
        ("LeftLeg", "l_thigh_001", "l_foot"),
        ("LeftFoot", "l_foot", "l_toe"),
        ("RightLeg", "r_thigh_001", "r_foot"),
        ("RightFoot", "r_foot", "r_toe"),
    )
    for name, start, end in target_chains:
        result = controller.add_retarget_chain(name, start, end, "")
        if str(result) != name:
            raise RuntimeError(f"failed target chain {name}: {start}->{end}, got {result}")
    unreal.EditorAssetLibrary.save_loaded_asset(target_rig, False)

    retarget_root, retarget_name = RETARGETER.rsplit("/", 1)
    retargeter = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        retarget_name, retarget_root, unreal.IKRetargeter, unreal.IKRetargetFactory()
    )
    retarget = unreal.IKRetargeterController.get_controller(retargeter)
    retarget.set_ik_rig(unreal.RetargetSourceOrTarget.SOURCE, source_rig)
    retarget.set_ik_rig(unreal.RetargetSourceOrTarget.TARGET, target_rig)
    retarget.set_preview_mesh(unreal.RetargetSourceOrTarget.SOURCE, source_mesh)
    retarget.set_preview_mesh(unreal.RetargetSourceOrTarget.TARGET, target_mesh)
    retarget.add_default_ops()
    for name, _start, _end in target_chains:
        if not retarget.set_source_chain(name, name):
            raise RuntimeError(f"failed source mapping for {name}")
    for bone, rotation in (
        ("l_upperarm", unreal.Rotator(0.0, 0.0, 35.0)),
        ("r_upperarm", unreal.Rotator(0.0, 0.0, -35.0)),
    ):
        retarget.set_rotation_offset_for_retarget_pose_bone(
            bone, rotation.quaternion(), unreal.RetargetSourceOrTarget.TARGET
        )
    unreal.EditorAssetLibrary.save_loaded_asset(retargeter, False)

    source_data = [unreal.EditorAssetLibrary.find_asset_data(path) for path in SOURCE_ANIMATIONS]
    inputs = unreal.IKRetargetBatchOperationInputs()
    inputs.set_editor_property("assets_to_retarget", source_data)
    inputs.set_editor_property("source_mesh", source_mesh)
    inputs.set_editor_property("target_mesh", target_mesh)
    inputs.set_editor_property("ik_retarget_asset", retargeter)
    inputs.set_editor_property("search", "AS_Gahyeon_")
    inputs.set_editor_property("replace", "AS_Diana_")
    inputs.set_editor_property("suffix", "_NeckHead_v372")
    inputs.set_editor_property("target_path", ANIMATION_ROOT)
    inputs.set_editor_property("use_source_path", False)
    inputs.set_editor_property("include_referenced_assets", False)
    inputs.set_editor_property("overwrite_existing_files", False)
    created = unreal.IKRetargetBatchOperation.run_batch_retarget(inputs)
    if len(created) != 3:
        raise RuntimeError(f"expected three animations, created {len(created)}")
    created_paths = [str(item.package_name) for item in created]
    for path in created_paths:
        unreal.EditorAssetLibrary.save_loaded_asset(require_asset(path), False)
    run = require_asset(next(path for path in created_paths if "RunForward" in path))
    motion = {
        bone: max_rotation_delta(run, bone)
        for bone in ("neck_0", neck_end, "head_002")
    }
    report = {
        "schemaVersion": 1,
        "iterations": ["v370", "v371", "v372"],
        "status": "draft-neck-head-retarget-built",
        "targetRig": TARGET_RIG,
        "retargeter": RETARGETER,
        "targetChains": [
            {"name": name, "start": start, "end": end}
            for name, start, end in target_chains
        ],
        "createdAnimations": created_paths,
        "runRotationDeltaDegrees": motion,
        "sourceRunRotationDeltaDegrees": {"neck_01": 10.8779, "head": 11.1699},
        "hypothesis": "Separate Neck and Head chains prevent head motion from collapsing onto Diana's neck root.",
        "visualValidationPending": True,
        "humanApproved": False,
        "productionReady": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("DIANA_V370_NECK_HEAD=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


build_diana_neck_head_retarget_v370()
