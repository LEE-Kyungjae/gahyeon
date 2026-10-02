"""Retarget the remaining imported motion donors directly onto Diana.

Run one immutable preset per editor invocation with GAHYEON_DIANA_MOTION.
The resulting body animation is deliberately followed by the component-space
visible-root bake; Diana's visible head lives in a disconnected bone tree.
"""

from pathlib import Path
import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hayley_motion_presets import CYBER_IMPORTED, MIXAMO_IMPORTED
from living_character_retarget import LivingCharacterRetargetConfig, build_living_character_retarget


ROOT = Path("/Users/ze/work/gahyeonbot")
TARGET_MESH = "/Game/Gahyeon/Character2/Diana/v024/Source/SK_Diana_CM_v024"
TARGET_CHAINS = (
    ("Spine", "spine_0", "neck_0"),
    ("Head", "neck_0", "head_002"),
    ("LeftClavicle", "l_shoulder", "l_shoulder"),
    ("LeftArm", "l_upperarm", "l_hand"),
    ("RightClavicle", "r_shoulder", "r_shoulder"),
    ("RightArm", "r_upperarm", "r_hand"),
    ("LeftLeg", "l_thigh_001", "l_foot"),
    ("LeftFoot", "l_foot", "l_toe"),
    ("RightLeg", "r_thigh_001", "r_foot"),
    ("RightFoot", "r_foot", "r_toe"),
)

PRESETS = {
    "active-idle": dict(
        iteration="v422",
        source_mesh_path="/Game/LivingCharacterPOC/v371/Donors/CyberIdle/whitehair_body_v2",
        source_animation_path="/Game/LivingCharacterPOC/v371/Donors/CyberIdle/Idle_Anim",
        source_root_bone="pelvis",
        source_chains=CYBER_IMPORTED,
        search="Idle_Anim",
        replace="AS_Diana_ActiveIdle",
    ),
    "walk-alt": dict(
        iteration="v423",
        source_mesh_path="/Game/LivingCharacterPOC/v371/Donors/GynoidWalk/FemBot_1000",
        source_animation_path="/Game/LivingCharacterPOC/v371/Donors/GynoidWalk/FemBot_1000_Anim",
        source_root_bone="Hips",
        source_chains=MIXAMO_IMPORTED,
        search="FemBot_1000_Anim",
        replace="AS_Diana_WalkAlt",
    ),
    "explain": dict(
        iteration="v424",
        source_mesh_path="/Game/LivingCharacterPOC/v371/Donors/HandsForward/Hands_Forward_Gesture",
        source_animation_path="/Game/LivingCharacterPOC/v371/Donors/HandsForward/Hands_Forward_Gesture_Anim",
        source_root_bone="Hips",
        source_chains=MIXAMO_IMPORTED,
        search="Hands_Forward_Gesture_Anim",
        replace="AS_Diana_Explain",
    ),
    "stand-sit": dict(
        iteration="v425",
        source_mesh_path="/Game/LivingCharacterPOC/v374/Donors/StandSitClean/StandSit_Clean_v001",
        source_animation_path="/Game/LivingCharacterPOC/v374/Donors/StandSitClean/StandSit_Clean_v001_Anim",
        source_root_bone="Hips",
        source_chains=MIXAMO_IMPORTED,
        search="StandSit_Clean_v001_Anim",
        replace="AS_Diana_StandSit",
    ),
    "narration": dict(
        iteration="v426",
        source_mesh_path="/Game/LivingCharacterPOC/v374/Donors/NarrationClean/Narration_Clean_v001",
        source_animation_path="/Game/LivingCharacterPOC/v374/Donors/NarrationClean/Narration_Clean_v001_Anim",
        source_root_bone="Hips",
        source_chains=MIXAMO_IMPORTED,
        search="Narration_Clean_v001_Anim",
        replace="AS_Diana_Narration",
    ),
}


def run(name: str):
    if name not in PRESETS:
        raise RuntimeError(f"unknown Diana motion preset {name!r}; choose {sorted(PRESETS)}")
    preset = dict(PRESETS[name])
    iteration = preset["iteration"]
    return build_living_character_retarget(LivingCharacterRetargetConfig(
        **preset,
        target_mesh_path=TARGET_MESH,
        asset_root=f"/Game/Gahyeon/Character2/Diana/{iteration}/Retarget",
        source_rig_name=f"IK_Donor_{iteration}",
        target_rig_name=f"IK_Diana_{iteration}",
        retargeter_name=f"RTG_DonorToDiana_{iteration}",
        animation_root=f"/Game/Gahyeon/Character2/Diana/{iteration}/Animation",
        target_root_bone="hip",
        target_chains=TARGET_CHAINS,
        suffix=f"_{iteration}",
        report_path=ROOT / "artifacts/gahyeon-ch/iterations" / f"{iteration}-diana-{name}-retarget" / "report.json",
        auto_align_target=True,
    ))


RESULT = run(os.environ.get("GAHYEON_DIANA_MOTION", "active-idle"))
