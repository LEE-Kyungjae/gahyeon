"""Retarget the Hands Forward explanatory gesture onto Hayley."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from living_character_retarget import LivingCharacterRetargetConfig, build_living_character_retarget


SOURCE_CHAINS = (
    ("Spine", "mixamorig:Hips", "mixamorig:Neck"), ("Head", "mixamorig:Neck", "mixamorig:Head"),
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
    ("Spine", "pelvis", "neck"), ("Head", "neck", "head"),
    ("LeftClavicle", "lScapula", "lScapula"), ("LeftArm", "lShoulder", "lHand"),
    ("RightClavicle", "rScapula", "rScapula"), ("RightArm", "rShoulder", "rHand"),
    ("LeftLeg", "lThigh", "lFoot"), ("LeftFoot", "lFoot", "lToe"),
    ("RightLeg", "rThigh", "rFoot"), ("RightFoot", "rFoot", "rToe"),
)


def retarget_hayley_hands_forward_v425():
    return build_living_character_retarget(LivingCharacterRetargetConfig(
        iteration="v425",
        source_mesh_path="/Game/LivingCharacterPOC/v371/Donors/HandsForward/Hands_Forward_Gesture",
        source_animation_path="/Game/LivingCharacterPOC/v371/Donors/HandsForward/Hands_Forward_Gesture_Anim",
        target_mesh_path="/Game/LivingCharacterPOC/v371/Characters/Hayley/Hayley2",
        asset_root="/Game/LivingCharacterPOC/v425/Retarget",
        source_rig_name="IK_HandsForward_Source_v425", target_rig_name="IK_Hayley_Target_v425",
        retargeter_name="RTG_HandsForwardToHayley_v425",
        animation_root="/Game/LivingCharacterPOC/v425/Animation",
        source_root_bone="mixamorig:Hips", target_root_bone="pelvis",
        source_chains=SOURCE_CHAINS, target_chains=TARGET_CHAINS,
        search="Hands_Forward_Gesture_Anim", replace="AS_Hayley_HandsForward", suffix="_v425",
        report_path=Path("/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v425-hayley-hands-forward-retarget/report.json"),
    ))


retarget_hayley_hands_forward_v425()
