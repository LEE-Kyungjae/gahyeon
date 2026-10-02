"""Retarget the correctly prefixed Cyber idle skeleton to clean Hayley."""

from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from hayley_motion_presets import TARGET
from living_character_retarget import LivingCharacterRetargetConfig, build_living_character_retarget


SOURCE = (
    ("Spine", "prefix_pelvis", "prefix_neck_01"),
    ("Head", "prefix_neck_01", "prefix_head"),
    ("LeftClavicle", "prefix_clavicle_l", "prefix_clavicle_l"),
    ("LeftArm", "prefix_upperarm_l", "prefix_hand_l"),
    ("RightClavicle", "prefix_clavicle_r", "prefix_clavicle_r"),
    ("RightArm", "prefix_upperarm_r", "prefix_hand_r"),
    ("LeftLeg", "prefix_thigh_l", "prefix_foot_l"),
    ("LeftFoot", "prefix_foot_l", "prefix_ball_l"),
    ("RightLeg", "prefix_thigh_r", "prefix_foot_r"),
    ("RightFoot", "prefix_foot_r", "prefix_ball_r"),
)


def retarget_cyber_idle_prefix_v466():
    return build_living_character_retarget(LivingCharacterRetargetConfig(
        iteration="v466",
        source_mesh_path="/Game/LivingCharacterPOC/v371/Donors/CyberIdle/prefix_whitehair_body_v2",
        source_animation_path="/Game/LivingCharacterPOC/v371/Donors/CyberIdle/Idle_Anim",
        target_mesh_path="/Game/LivingCharacterPOC/v448/Characters/HayleyBindClean/Hayley_BindPoseClean_v447",
        asset_root="/Game/LivingCharacterPOC/v466/Retarget",
        source_rig_name="IK_CyberPrefix_Source_v466",
        target_rig_name="IK_HayleyClean_Target_v466",
        retargeter_name="RTG_CyberPrefixIdleToHayleyClean_v466",
        animation_root="/Game/LivingCharacterPOC/v466/Animation",
        source_root_bone="prefix_pelvis",
        target_root_bone="pelvis",
        source_chains=SOURCE,
        target_chains=TARGET,
        search="Idle_Anim",
        replace="AS_HayleyClean_CyberIdle",
        suffix="_v466",
        report_path=Path(
            "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v466-hayley-clean-cyber-idle-retarget/report.json"
        ),
        auto_align_target=True,
    ))


RESULT = retarget_cyber_idle_prefix_v466()
