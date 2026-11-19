"""Verified post-import skeleton presets for Hayley motion retargeting."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from living_character_retarget import LivingCharacterRetargetConfig, build_living_character_retarget


TARGET = (
    ("Spine", "pelvis", "neck"), ("Head", "neck", "head"),
    ("LeftClavicle", "lScapula", "lScapula"), ("LeftArm", "lShoulder", "lHand"),
    ("RightClavicle", "rScapula", "rScapula"), ("RightArm", "rShoulder", "rHand"),
    ("LeftLeg", "lThigh", "lFoot"), ("LeftFoot", "lFoot", "lToe"),
    ("RightLeg", "rThigh", "rFoot"), ("RightFoot", "rFoot", "rToe"),
)
MIXAMO_IMPORTED = (
    ("Spine", "Hips", "Neck"), ("Head", "Neck", "Head"),
    ("LeftClavicle", "LeftShoulder", "LeftShoulder"), ("LeftArm", "LeftArm", "LeftHand"),
    ("RightClavicle", "RightShoulder", "RightShoulder"), ("RightArm", "RightArm", "RightHand"),
    ("LeftLeg", "LeftUpLeg", "LeftFoot"), ("LeftFoot", "LeftFoot", "LeftToeBase"),
    ("RightLeg", "RightUpLeg", "RightFoot"), ("RightFoot", "RightFoot", "RightToeBase"),
)
CYBER_IMPORTED = (
    ("Spine", "pelvis", "neck_01"), ("Head", "neck_01", "head"),
    ("LeftClavicle", "clavicle_l", "clavicle_l"), ("LeftArm", "upperarm_l", "hand_l"),
    ("RightClavicle", "clavicle_r", "clavicle_r"), ("RightArm", "upperarm_r", "hand_r"),
    ("LeftLeg", "thigh_l", "foot_l"), ("LeftFoot", "foot_l", "ball_l"),
    ("RightLeg", "thigh_r", "foot_r"), ("RightFoot", "foot_r", "ball_r"),
)
PRESETS = {
    "cyber-idle-v428": dict(
        iteration="v428", source_mesh_path="/Game/LivingCharacterPOC/v371/Donors/CyberIdle/whitehair_body_v2",
        source_animation_path="/Game/LivingCharacterPOC/v371/Donors/CyberIdle/Idle_Anim",
        source_root_bone="pelvis", source_chains=CYBER_IMPORTED, search="Idle_Anim",
        replace="AS_Hayley_CyberIdle", suffix="_v428", label="hayley-cyber-idle-retarget",
    ),
    "hands-forward-v429": dict(
        iteration="v429", source_mesh_path="/Game/LivingCharacterPOC/v371/Donors/HandsForward/Hands_Forward_Gesture",
        source_animation_path="/Game/LivingCharacterPOC/v371/Donors/HandsForward/Hands_Forward_Gesture_Anim",
        source_root_bone="Hips", source_chains=MIXAMO_IMPORTED, search="Hands_Forward_Gesture_Anim",
        replace="AS_Hayley_HandsForward", suffix="_v429", label="hayley-hands-forward-retarget",
    ),
    "stand-sit-v430": dict(
        iteration="v430", source_mesh_path="/Game/LivingCharacterPOC/v374/Donors/StandSitClean/StandSit_Clean_v001",
        source_animation_path="/Game/LivingCharacterPOC/v374/Donors/StandSitClean/StandSit_Clean_v001_Anim",
        source_root_bone="Hips", source_chains=MIXAMO_IMPORTED, search="StandSit_Clean_v001_Anim",
        replace="AS_Hayley_StandSit", suffix="_v430", label="hayley-stand-sit-retarget",
    ),
}


def run_hayley_motion_preset(name):
    preset = dict(PRESETS[name])
    label = preset.pop("label")
    iteration = preset["iteration"]
    return build_living_character_retarget(LivingCharacterRetargetConfig(
        **preset,
        target_mesh_path="/Game/LivingCharacterPOC/v371/Characters/Hayley/Hayley2",
        asset_root=f"/Game/LivingCharacterPOC/{iteration}/Retarget",
        source_rig_name=f"IK_Source_{iteration}", target_rig_name=f"IK_Hayley_Target_{iteration}",
        retargeter_name=f"RTG_ToHayley_{iteration}", animation_root=f"/Game/LivingCharacterPOC/{iteration}/Animation",
        target_root_bone="pelvis", target_chains=TARGET,
        report_path=Path(f"/Users/ze/work/gahyeonbot/artifacts/living-character-poc-{iteration}-{label}/report.json"),
    ))
