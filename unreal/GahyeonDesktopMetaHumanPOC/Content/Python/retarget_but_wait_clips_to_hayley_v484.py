"""Retarget three selected short But-wait gestures to clean Hayley."""

from pathlib import Path
import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hayley_motion_presets import MIXAMO_IMPORTED, TARGET
from living_character_retarget import LivingCharacterRetargetConfig, build_living_character_retarget


CLIPS = (
    ("subtle", "segment-01", "segment-01-frames-0211-0287"),
    ("present", "segment-02", "segment-02-frames-0323-0399"),
    ("emphasis", "segment-05", "segment-05-frames-0858-0934"),
)


def retarget_but_wait_clips_to_hayley_v484():
    requested = os.environ.get("GAHYEON_BUT_WAIT_CLIP")
    matches = [clip for clip in CLIPS if clip[0] == requested]
    if len(matches) != 1:
        raise RuntimeError(f"set GAHYEON_BUT_WAIT_CLIP to one of {[clip[0] for clip in CLIPS]}")
    label, segment, asset_name = matches[0]
    source_root = f"/Game/LivingCharacterPOC/v482/Donors/ButWait/{segment}/{asset_name}"
    return build_living_character_retarget(LivingCharacterRetargetConfig(
            iteration="v484",
            source_mesh_path=source_root,
            source_animation_path=f"{source_root}_Anim",
            target_mesh_path="/Game/LivingCharacterPOC/v448/Characters/HayleyBindClean/Hayley_BindPoseClean_v447",
            asset_root=f"/Game/LivingCharacterPOC/v484/Retarget/{label}",
            source_rig_name=f"IK_ButWait_{label}_v484",
            target_rig_name=f"IK_HayleyClean_{label}_v484",
            retargeter_name=f"RTG_ButWait_{label}_ToHayley_v484",
            animation_root=f"/Game/LivingCharacterPOC/v484/Animation/{label}",
            source_root_bone="Hips", target_root_bone="pelvis",
            source_chains=MIXAMO_IMPORTED, target_chains=TARGET,
            search=f"{asset_name}_Anim", replace=f"AS_HayleyClean_ButWait_{label}",
            suffix="_v484",
            report_path=Path(
                f"/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v484-hayley-but-wait-retarget/{label}/report.json"
            ),
            auto_align_target=True,
        ))


RESULT = retarget_but_wait_clips_to_hayley_v484()
