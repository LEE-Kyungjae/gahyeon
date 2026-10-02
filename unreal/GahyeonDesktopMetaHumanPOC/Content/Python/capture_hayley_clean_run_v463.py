"""Capture three evaluated phases of the lower-body-only Hayley run layer."""

from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import capture_hayley_segmented_spawned_v439 as capture


capture.ITERATION = "v463"
capture.MAP = "/Game/LivingCharacterPOC/v463/QA/L_HayleyCleanRunLower_v463"
capture.MESH = "/Game/LivingCharacterPOC/v448/Characters/HayleyBindClean/Hayley_BindPoseClean_v447"
capture.SOURCE_SCALE = 1.0
capture.EVALUATE_BEFORE_FREEZE = True
capture.ANIMATIONS = (
    ("run-lower", "/Game/LivingCharacterPOC/v462/Animation/AS_HayleyClean_RunLower_v462"),
)
capture.OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v463-hayley-clean-run-lower-evidence"
)


def capture_hayley_clean_run_v463():
    capture.capture_hayley_segmented_spawned_v439()


capture_hayley_clean_run_v463()
