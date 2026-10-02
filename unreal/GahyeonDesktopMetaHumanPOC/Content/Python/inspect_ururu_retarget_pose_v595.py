"""Record Ururu's current target retarget-pose offsets before correction."""

import json
from pathlib import Path

import unreal


RETARGETER = "/Game/LivingCharacterPOC/v586/Retarget/RTG_Hayley_Ururu_v586"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/"
    "living-character-poc-v595-ururu-retarget-pose-inspection/report.json"
)
BONES = (
    "ValveBiped_Bip01_Spine4",
    "ValveBiped_Bip01_Neck1",
    "ValveBiped_Bip01_Head1",
    "ValveBiped_Bip01_L_Clavicle",
    "ValveBiped_Bip01_L_UpperArm",
    "ValveBiped_Bip01_R_Clavicle",
    "ValveBiped_Bip01_R_UpperArm",
)


def inspect_ururu_retarget_pose_v595():
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to overwrite immutable output: {OUTPUT}")
    asset = unreal.load_asset(RETARGETER)
    if asset is None:
        raise RuntimeError(f"missing retargeter: {RETARGETER}")
    controller = unreal.IKRetargeterController.get_controller(asset)
    offsets = {}
    for bone in BONES:
        value = controller.get_rotation_offset_for_retarget_pose_bone(
            bone, unreal.RetargetSourceOrTarget.TARGET
        )
        offsets[bone] = {key: getattr(value, key) for key in ("x", "y", "z", "w")}
    report = {
        "schemaVersion": 1,
        "iteration": "v595",
        "status": "read-only-retarget-pose-inspection",
        "retargeter": RETARGETER,
        "targetOffsets": offsets,
        "humanApproved": False,
        "releaseEligible": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.log("URURU_RETARGET_POSE_V595=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


inspect_ururu_retarget_pose_v595()
