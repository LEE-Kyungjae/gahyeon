"""Capture explain and stand/sit phases on the corrected Hayley target."""

from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import capture_hayley_segmented_spawned_v439 as capture


capture.ITERATION = "v457"
capture.MAP = "/Game/LivingCharacterPOC/v457/QA/L_HayleyCleanMotion_v457"
capture.MESH = "/Game/LivingCharacterPOC/v448/Characters/HayleyBindClean/Hayley_BindPoseClean_v447"
capture.SOURCE_SCALE = 1.0
capture.EVALUATE_BEFORE_FREEZE = True
capture.ANIMATIONS = (
    ("explain", "/Game/LivingCharacterPOC/v451/Animation/AS_HayleyClean_HandsForward_v451"),
    ("stand-sit", "/Game/LivingCharacterPOC/v452/Animation/AS_HayleyClean_StandSit_v452"),
)
capture.OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v457-hayley-clean-motion-evidence"
)


def capture_hayley_clean_motion_v453():
    capture.capture_hayley_segmented_spawned_v439()


capture_hayley_clean_motion_v453()
