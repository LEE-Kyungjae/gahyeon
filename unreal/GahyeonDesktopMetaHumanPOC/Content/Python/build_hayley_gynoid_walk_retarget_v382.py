"""Build the corrected namespace-free Gynoid-walk to Hayley retarget."""

from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from living_character_retarget import (  # noqa: E402
    LivingCharacterRetargetConfig,
    build_living_character_retarget,
)


SOURCE_CHAINS = (
    ("Spine", "Hips", "Neck"),
    ("Head", "Neck", "Head"),
    ("LeftClavicle", "LeftShoulder", "LeftShoulder"),
    ("LeftArm", "LeftArm", "LeftHand"),
    ("RightClavicle", "RightShoulder", "RightShoulder"),
    ("RightArm", "RightArm", "RightHand"),
    ("LeftLeg", "LeftUpLeg", "LeftFoot"),
    ("LeftFoot", "LeftFoot", "LeftToeBase"),
    ("RightLeg", "RightUpLeg", "RightFoot"),
    ("RightFoot", "RightFoot", "RightToeBase"),
)
TARGET_CHAINS = (
    ("Spine", "pelvis", "neck"),
    ("Head", "neck", "head"),
    ("LeftClavicle", "lScapula", "lScapula"),
    ("LeftArm", "lShoulder", "lHand"),
    ("RightClavicle", "rScapula", "rScapula"),
    ("RightArm", "rShoulder", "rHand"),
    ("LeftLeg", "lThigh", "lFoot"),
    ("LeftFoot", "lFoot", "lToe"),
    ("RightLeg", "rThigh", "rFoot"),
    ("RightFoot", "rFoot", "rToe"),
)
CONFIG = LivingCharacterRetargetConfig(
    iteration="v382",
    source_mesh_path="/Game/LivingCharacterPOC/v371/Donors/GynoidWalk/FemBot_1000",
    source_animation_path="/Game/LivingCharacterPOC/v371/Donors/GynoidWalk/FemBot_1000_Anim",
    target_mesh_path="/Game/LivingCharacterPOC/v371/Characters/Hayley/Hayley2",
    asset_root="/Game/LivingCharacterPOC/v382/Retarget",
    source_rig_name="IK_GynoidMixamo_Source_v382",
    target_rig_name="IK_Hayley_Target_v382",
    retargeter_name="RTG_GynoidWalkToHayley_v382",
    animation_root="/Game/LivingCharacterPOC/v382/Animation",
    source_root_bone="Hips",
    target_root_bone="pelvis",
    source_chains=SOURCE_CHAINS,
    target_chains=TARGET_CHAINS,
    search="FemBot_1000_Anim",
    replace="AS_Hayley_GynoidWalk",
    suffix="_v382",
    report_path=Path(
        "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v382-gynoid-walk-retarget/report.json"
    ),
)
build_living_character_retarget(CONFIG)
