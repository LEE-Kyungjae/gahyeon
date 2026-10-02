"""Capture three phases from each selected But-wait gesture on Hayley."""

from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import capture_hayley_segmented_spawned_v439 as capture


capture.ITERATION = "v485"
capture.MAP = "/Game/LivingCharacterPOC/v485/QA/L_HayleyButWaitGestures_v485"
capture.MESH = "/Game/LivingCharacterPOC/v448/Characters/HayleyBindClean/Hayley_BindPoseClean_v447"
capture.SOURCE_SCALE = 1.0
capture.EVALUATE_BEFORE_FREEZE = True
capture.ANIMATIONS = (
    ("subtle", "/Game/LivingCharacterPOC/v484/Animation/subtle/AS_HayleyClean_ButWait_subtle_v484"),
    ("present", "/Game/LivingCharacterPOC/v484/Animation/present/AS_HayleyClean_ButWait_present_v484"),
    ("emphasis", "/Game/LivingCharacterPOC/v484/Animation/emphasis/AS_HayleyClean_ButWait_emphasis_v484"),
)
capture.OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v485-hayley-but-wait-evidence"
)


def capture_hayley_but_wait_v485():
    capture.capture_hayley_segmented_spawned_v439()


capture_hayley_but_wait_v485()
