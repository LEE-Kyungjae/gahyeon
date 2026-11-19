"""Per-segment chain retarget presets that do not dilute motion across Hayley twist bones."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from living_character_retarget import LivingCharacterRetargetConfig, build_living_character_retarget


SOURCE = (
    ("Spine", "Hips", "Neck"), ("Head", "Neck", "Head"),
    ("LeftClavicle", "LeftShoulder", "LeftShoulder"),
    ("LeftUpperArm", "LeftArm", "LeftArm"), ("LeftForeArm", "LeftForeArm", "LeftForeArm"),
    ("LeftHand", "LeftHand", "LeftHand"),
    ("RightClavicle", "RightShoulder", "RightShoulder"),
    ("RightUpperArm", "RightArm", "RightArm"), ("RightForeArm", "RightForeArm", "RightForeArm"),
    ("RightHand", "RightHand", "RightHand"),
    ("LeftThigh", "LeftUpLeg", "LeftUpLeg"), ("LeftKnee", "LeftLeg", "LeftLeg"),
    ("LeftFoot", "LeftFoot", "LeftFoot"), ("LeftToe", "LeftToeBase", "LeftToeBase"),
    ("RightThigh", "RightUpLeg", "RightUpLeg"), ("RightKnee", "RightLeg", "RightLeg"),
    ("RightFoot", "RightFoot", "RightFoot"), ("RightToe", "RightToeBase", "RightToeBase"),
)
TARGET = (
    ("Spine", "pelvis", "neck"), ("Head", "neck", "head"),
    ("LeftClavicle", "lScapula", "lScapula"),
    ("LeftUpperArm", "lShoulder", "lShoulder"), ("LeftForeArm", "lForearm", "lForearm"),
    ("LeftHand", "lHand", "lHand"),
    ("RightClavicle", "rScapula", "rScapula"),
    ("RightUpperArm", "rShoulder", "rShoulder"), ("RightForeArm", "rForearm", "rForearm"),
    ("RightHand", "rHand", "rHand"),
    ("LeftThigh", "lThigh", "lThigh"), ("LeftKnee", "lKnee", "lKnee"),
    ("LeftFoot", "lFoot", "lFoot"), ("LeftToe", "lToe", "lToe"),
    ("RightThigh", "rThigh", "rThigh"), ("RightKnee", "rKnee", "rKnee"),
    ("RightFoot", "rFoot", "rFoot"), ("RightToe", "rToe", "rToe"),
)
PRESETS = {
    "explain": dict(iteration="v435", source_mesh_path="/Game/LivingCharacterPOC/v371/Donors/HandsForward/Hands_Forward_Gesture", source_animation_path="/Game/LivingCharacterPOC/v371/Donors/HandsForward/Hands_Forward_Gesture_Anim", search="Hands_Forward_Gesture_Anim", replace="AS_Hayley_HandsForwardSegmented", suffix="_v435", label="hayley-hands-forward-segment-retarget"),
    "stand-sit": dict(iteration="v436", source_mesh_path="/Game/LivingCharacterPOC/v374/Donors/StandSitClean/StandSit_Clean_v001", source_animation_path="/Game/LivingCharacterPOC/v374/Donors/StandSitClean/StandSit_Clean_v001_Anim", search="StandSit_Clean_v001_Anim", replace="AS_Hayley_StandSitSegmented", suffix="_v436", label="hayley-stand-sit-segment-retarget"),
}


def run_segment_retarget_v435(name):
    preset = dict(PRESETS[name])
    label = preset.pop("label")
    iteration = preset["iteration"]
    return build_living_character_retarget(LivingCharacterRetargetConfig(
        **preset,
        target_mesh_path="/Game/LivingCharacterPOC/v371/Characters/Hayley/Hayley2",
        asset_root=f"/Game/LivingCharacterPOC/{iteration}/Retarget",
        source_rig_name=f"IK_Source_{iteration}", target_rig_name=f"IK_Hayley_Target_{iteration}",
        retargeter_name=f"RTG_SegmentedToHayley_{iteration}", animation_root=f"/Game/LivingCharacterPOC/{iteration}/Animation",
        source_root_bone="Hips", target_root_bone="pelvis", source_chains=SOURCE, target_chains=TARGET,
        report_path=Path(f"/Users/ze/work/gahyeonbot/artifacts/living-character-poc-{iteration}-{label}/report.json"),
    ))
