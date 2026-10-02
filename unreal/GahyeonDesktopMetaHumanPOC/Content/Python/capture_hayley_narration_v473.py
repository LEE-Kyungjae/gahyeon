"""Capture three evaluated phases of the retargeted narration performance."""

from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import capture_hayley_segmented_spawned_v439 as capture


capture.ITERATION = "v473"
capture.MAP = "/Game/LivingCharacterPOC/v473/QA/L_HayleyNarration_v473"
capture.MESH = "/Game/LivingCharacterPOC/v448/Characters/HayleyBindClean/Hayley_BindPoseClean_v447"
capture.SOURCE_SCALE = 1.0
capture.EVALUATE_BEFORE_FREEZE = True
capture.ANIMATIONS = (
    ("narration", "/Game/LivingCharacterPOC/v472/Animation/AS_HayleyClean_Narration_v472"),
)
capture.OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v473-hayley-narration-evidence"
)


def capture_hayley_narration_v473():
    capture.capture_hayley_segmented_spawned_v439()


capture_hayley_narration_v473()
