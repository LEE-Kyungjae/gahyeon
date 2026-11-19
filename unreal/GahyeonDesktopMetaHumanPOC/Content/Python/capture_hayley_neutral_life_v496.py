"""Capture three full-body phases of Hayley's restrained neutral life loop."""

from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import capture_hayley_segmented_spawned_v439 as capture


capture.ITERATION = "v496"
capture.MAP = "/Game/LivingCharacterPOC/v496/QA/L_HayleyNeutralLife_v496"
capture.MESH = "/Game/LivingCharacterPOC/v448/Characters/HayleyBindClean/Hayley_BindPoseClean_v447"
capture.SOURCE_SCALE = 1.0
capture.EVALUATE_BEFORE_FREEZE = True
capture.ANIMATIONS = (("neutral-life", "/Game/LivingCharacterPOC/v495/Animation/Hayley_NeutralLife_v494"),)
capture.OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v496-hayley-neutral-life-body-evidence"
)


def capture_hayley_neutral_life_v496():
    capture.capture_hayley_segmented_spawned_v439()


capture_hayley_neutral_life_v496()
