"""Retarget the Cyber Girl standing idle onto Hayley."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from living_character_retarget import LivingCharacterRetargetConfig, build_living_character_retarget


SOURCE_CHAINS = (
    ("Spine", "prefix_pelvis", "prefix_neck_01"), ("Head", "prefix_neck_01", "prefix_head"),
    ("LeftClavicle", "prefix_clavicle_l", "prefix_clavicle_l"),
    ("LeftArm", "prefix_upperarm_l", "prefix_hand_l"),
    ("RightClavicle", "prefix_clavicle_r", "prefix_clavicle_r"),
    ("RightArm", "prefix_upperarm_r", "prefix_hand_r"),
    ("LeftLeg", "prefix_thigh_l", "prefix_foot_l"), ("LeftFoot", "prefix_foot_l", "prefix_ball_l"),
    ("RightLeg", "prefix_thigh_r", "prefix_foot_r"), ("RightFoot", "prefix_foot_r", "prefix_ball_r"),
)
TARGET_CHAINS = (
    ("Spine", "pelvis", "neck"), ("Head", "neck", "head"),
    ("LeftClavicle", "lScapula", "lScapula"), ("LeftArm", "lShoulder", "lHand"),
    ("RightClavicle", "rScapula", "rScapula"), ("RightArm", "rShoulder", "rHand"),
    ("LeftLeg", "lThigh", "lFoot"), ("LeftFoot", "lFoot", "lToe"),
    ("RightLeg", "rThigh", "rFoot"), ("RightFoot", "rFoot", "rToe"),
)


def retarget_hayley_cyber_idle_v424():
    return build_living_character_retarget(LivingCharacterRetargetConfig(
        iteration="v424",
        source_mesh_path="/Game/LivingCharacterPOC/v371/Donors/CyberIdle/whitehair_body_v2",
        source_animation_path="/Game/LivingCharacterPOC/v371/Donors/CyberIdle/Idle_Anim",
        target_mesh_path="/Game/LivingCharacterPOC/v371/Characters/Hayley/Hayley2",
        asset_root="/Game/LivingCharacterPOC/v424/Retarget",
        source_rig_name="IK_CyberIdle_Source_v424", target_rig_name="IK_Hayley_Target_v424",
        retargeter_name="RTG_CyberIdleToHayley_v424",
        animation_root="/Game/LivingCharacterPOC/v424/Animation",
        source_root_bone="prefix_pelvis", target_root_bone="pelvis",
        source_chains=SOURCE_CHAINS, target_chains=TARGET_CHAINS,
        search="Idle_Anim", replace="AS_Hayley_CyberIdle", suffix="_v424",
        report_path=Path("/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v424-hayley-cyber-idle-retarget/report.json"),
    ))


retarget_hayley_cyber_idle_v424()
