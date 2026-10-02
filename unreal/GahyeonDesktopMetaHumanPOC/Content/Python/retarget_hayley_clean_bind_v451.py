"""Retarget motion donors to the corrected Hayley bind-pose mesh."""

from pathlib import Path
import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hayley_motion_presets import MIXAMO_IMPORTED, TARGET
from living_character_retarget import LivingCharacterRetargetConfig, build_living_character_retarget


PRESETS = {
    "explain": dict(
        iteration="v451",
        source_mesh_path="/Game/LivingCharacterPOC/v371/Donors/HandsForward/Hands_Forward_Gesture",
        source_animation_path="/Game/LivingCharacterPOC/v371/Donors/HandsForward/Hands_Forward_Gesture_Anim",
        search="Hands_Forward_Gesture_Anim",
        replace="AS_HayleyClean_HandsForward",
        suffix="_v451",
        label="hayley-clean-hands-forward-retarget",
    ),
    "stand-sit": dict(
        iteration="v452",
        source_mesh_path="/Game/LivingCharacterPOC/v374/Donors/StandSitClean/StandSit_Clean_v001",
        source_animation_path="/Game/LivingCharacterPOC/v374/Donors/StandSitClean/StandSit_Clean_v001_Anim",
        search="StandSit_Clean_v001_Anim",
        replace="AS_HayleyClean_StandSit",
        suffix="_v452",
        label="hayley-clean-stand-sit-retarget",
    ),
    "walk": dict(
        iteration="v459",
        source_mesh_path="/Game/LivingCharacterPOC/v371/Donors/GynoidWalk/FemBot_1000",
        source_animation_path="/Game/LivingCharacterPOC/v371/Donors/GynoidWalk/FemBot_1000_Anim",
        search="FemBot_1000_Anim",
        replace="AS_HayleyClean_Walk",
        suffix="_v459",
        label="hayley-clean-walk-retarget",
    ),
}


def run_clean_bind_retarget_v451(name: str):
    preset = dict(PRESETS[name])
    label = preset.pop("label")
    iteration = preset["iteration"]
    return build_living_character_retarget(LivingCharacterRetargetConfig(
        **preset,
        target_mesh_path="/Game/LivingCharacterPOC/v448/Characters/HayleyBindClean/Hayley_BindPoseClean_v447",
        asset_root=f"/Game/LivingCharacterPOC/{iteration}/Retarget",
        source_rig_name=f"IK_Source_{iteration}",
        target_rig_name=f"IK_HayleyClean_Target_{iteration}",
        retargeter_name=f"RTG_AutoAlignedToHayleyClean_{iteration}",
        animation_root=f"/Game/LivingCharacterPOC/{iteration}/Animation",
        source_root_bone="Hips",
        target_root_bone="pelvis",
        source_chains=MIXAMO_IMPORTED,
        target_chains=TARGET,
        report_path=Path(
            f"/Users/ze/work/gahyeonbot/artifacts/living-character-poc-{iteration}-{label}/report.json"
        ),
        auto_align_target=True,
    ))


RESULT = run_clean_bind_retarget_v451(os.environ.get("GAHYEON_HAYLEY_MOTION", "explain"))
