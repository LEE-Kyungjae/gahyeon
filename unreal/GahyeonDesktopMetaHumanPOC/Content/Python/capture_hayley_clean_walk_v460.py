"""Capture three evaluated phases of the clean-target Hayley walk."""

from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import capture_hayley_segmented_spawned_v439 as capture


capture.ITERATION = "v460"
capture.MAP = "/Game/LivingCharacterPOC/v460/QA/L_HayleyCleanWalk_v460"
capture.MESH = "/Game/LivingCharacterPOC/v448/Characters/HayleyBindClean/Hayley_BindPoseClean_v447"
capture.SOURCE_SCALE = 1.0
capture.EVALUATE_BEFORE_FREEZE = True
capture.ANIMATIONS = (
    ("walk", "/Game/LivingCharacterPOC/v459/Animation/AS_HayleyClean_Walk_v459"),
)
capture.OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v460-hayley-clean-walk-evidence"
)


def capture_hayley_clean_walk_v460():
    capture.capture_hayley_segmented_spawned_v439()


capture_hayley_clean_walk_v460()
