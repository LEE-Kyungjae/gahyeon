"""Build a lower-body-only Luoli run layer on corrected Hayley."""

from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from living_character_retarget import LivingCharacterRetargetConfig, build_living_character_retarget


SOURCE = (
    ("Spine", "Hips", "Upperchest"),
    ("LeftLeg", "L_Upperleg", "L_Foot"),
    ("LeftFoot", "L_Foot", "L_ToeBase"),
    ("RightLeg", "R_UpperReg", "R_Foot"),
    ("RightFoot", "R_Foot", "R_ToeBase"),
)
TARGET = (
    ("Spine", "pelvis", "neck"),
    ("LeftLeg", "lThigh", "lFoot"),
    ("LeftFoot", "lFoot", "lToe"),
    ("RightLeg", "rThigh", "rFoot"),
    ("RightFoot", "rFoot", "rToe"),
)


def retarget_luoli_run_lower_v462():
    return build_living_character_retarget(LivingCharacterRetargetConfig(
        iteration="v462",
        source_mesh_path="/Game/LivingCharacterPOC/v461/Donors/LuoliRun/luoli_run_triangle",
        source_animation_path="/Game/LivingCharacterPOC/v461/Donors/LuoliRun/luoli_run_triangle_Anim",
        target_mesh_path="/Game/LivingCharacterPOC/v448/Characters/HayleyBindClean/Hayley_BindPoseClean_v447",
        asset_root="/Game/LivingCharacterPOC/v462/Retarget",
        source_rig_name="IK_LuoliRunLower_Source_v462",
        target_rig_name="IK_HayleyCleanLower_Target_v462",
        retargeter_name="RTG_LuoliRunLowerToHayleyClean_v462",
        animation_root="/Game/LivingCharacterPOC/v462/Animation",
        source_root_bone="Hips",
        target_root_bone="pelvis",
        source_chains=SOURCE,
        target_chains=TARGET,
        search="luoli_run_triangle_Anim",
        replace="AS_HayleyClean_RunLower",
        suffix="_v462",
        report_path=Path(
            "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v462-hayley-clean-run-lower-retarget/report.json"
        ),
        auto_align_target=True,
    ))


RESULT = retarget_luoli_run_lower_v462()
