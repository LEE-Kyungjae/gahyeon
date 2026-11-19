"""Auto-aligned target-pose retarget presets for Hayley."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hayley_segment_retarget_v435 import SOURCE, TARGET
from living_character_retarget import LivingCharacterRetargetConfig, build_living_character_retarget


PRESETS = {
    "explain": dict(iteration="v440", source_mesh_path="/Game/LivingCharacterPOC/v371/Donors/HandsForward/Hands_Forward_Gesture", source_animation_path="/Game/LivingCharacterPOC/v371/Donors/HandsForward/Hands_Forward_Gesture_Anim", search="Hands_Forward_Gesture_Anim", replace="AS_Hayley_HandsForwardAutoAligned", suffix="_v440", label="hayley-hands-forward-autoaligned-retarget"),
    "stand-sit": dict(iteration="v441", source_mesh_path="/Game/LivingCharacterPOC/v374/Donors/StandSitClean/StandSit_Clean_v001", source_animation_path="/Game/LivingCharacterPOC/v374/Donors/StandSitClean/StandSit_Clean_v001_Anim", search="StandSit_Clean_v001_Anim", replace="AS_Hayley_StandSitAutoAligned", suffix="_v441", label="hayley-stand-sit-autoaligned-retarget"),
}


def run_autoaligned_retarget_v440(name):
    preset = dict(PRESETS[name])
    label = preset.pop("label")
    iteration = preset["iteration"]
    return build_living_character_retarget(LivingCharacterRetargetConfig(
        **preset,
        target_mesh_path="/Game/LivingCharacterPOC/v371/Characters/Hayley/Hayley2",
        asset_root=f"/Game/LivingCharacterPOC/{iteration}/Retarget",
        source_rig_name=f"IK_Source_{iteration}", target_rig_name=f"IK_Hayley_Target_{iteration}",
        retargeter_name=f"RTG_AutoAlignedToHayley_{iteration}", animation_root=f"/Game/LivingCharacterPOC/{iteration}/Animation",
        source_root_bone="Hips", target_root_bone="pelvis", source_chains=SOURCE, target_chains=TARGET,
        report_path=Path(f"/Users/ze/work/gahyeonbot/artifacts/living-character-poc-{iteration}-{label}/report.json"),
        auto_align_target=True,
    ))
