"""Retarget the cleaned stand/sit transition onto Hayley."""

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


def retarget_hayley_stand_sit_v426():
    return build_living_character_retarget(LivingCharacterRetargetConfig(
        iteration="v426",
        source_mesh_path="/Game/LivingCharacterPOC/v374/Donors/StandSitClean/StandSit_Clean_v001",
        source_animation_path="/Game/LivingCharacterPOC/v374/Donors/StandSitClean/StandSit_Clean_v001_Anim",
        target_mesh_path="/Game/LivingCharacterPOC/v371/Characters/Hayley/Hayley2",
        asset_root="/Game/LivingCharacterPOC/v426/Retarget",
        source_rig_name="IK_StandSit_Source_v426", target_rig_name="IK_Hayley_Target_v426",
        retargeter_name="RTG_StandSitToHayley_v426",
        animation_root="/Game/LivingCharacterPOC/v426/Animation",
        source_root_bone="mixamorig:Hips", target_root_bone="pelvis",
        source_chains=SOURCE_CHAINS, target_chains=TARGET_CHAINS,
        search="StandSit_Clean_v001_Anim", replace="AS_Hayley_StandSit", suffix="_v426",
        report_path=Path("/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v426-hayley-stand-sit-retarget/report.json"),
    ))


retarget_hayley_stand_sit_v426()
