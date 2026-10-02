"""Retarget the cleaned narration performance to the clean Hayley character."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hayley_motion_presets import MIXAMO_IMPORTED, TARGET
from living_character_retarget import LivingCharacterRetargetConfig, build_living_character_retarget


def retarget_narration_to_hayley_v472():
    return build_living_character_retarget(LivingCharacterRetargetConfig(
        iteration="v472",
        source_mesh_path="/Game/LivingCharacterPOC/v374/Donors/NarrationClean/Narration_Clean_v001",
        source_animation_path="/Game/LivingCharacterPOC/v374/Donors/NarrationClean/Narration_Clean_v001_Anim",
        target_mesh_path="/Game/LivingCharacterPOC/v448/Characters/HayleyBindClean/Hayley_BindPoseClean_v447",
        asset_root="/Game/LivingCharacterPOC/v472/Retarget",
        source_rig_name="IK_Source_v472",
        target_rig_name="IK_HayleyClean_Target_v472",
        retargeter_name="RTG_NarrationToHayleyClean_v472",
        animation_root="/Game/LivingCharacterPOC/v472/Animation",
        source_root_bone="Hips",
        target_root_bone="pelvis",
        source_chains=MIXAMO_IMPORTED,
        target_chains=TARGET,
        search="Narration_Clean_v001_Anim",
        replace="AS_HayleyClean_Narration",
        suffix="_v472",
        report_path=Path(
            "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v472-hayley-narration-retarget/report.json"
        ),
        auto_align_target=True,
    ))


RESULT = retarget_narration_to_hayley_v472()
