"""Capture three evaluated phases of the correctly prefixed Cyber idle."""

from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import capture_hayley_segmented_spawned_v439 as capture


capture.ITERATION = "v467"
capture.MAP = "/Game/LivingCharacterPOC/v467/QA/L_HayleyCleanIdle_v467"
capture.MESH = "/Game/LivingCharacterPOC/v448/Characters/HayleyBindClean/Hayley_BindPoseClean_v447"
capture.SOURCE_SCALE = 1.0
capture.EVALUATE_BEFORE_FREEZE = True
capture.ANIMATIONS = (
    ("idle", "/Game/LivingCharacterPOC/v466/Animation/AS_HayleyClean_CyberIdle_v466"),
)
capture.OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v467-hayley-clean-idle-evidence"
)


def capture_hayley_clean_idle_v467():
    capture.capture_hayley_segmented_spawned_v439()


capture_hayley_clean_idle_v467()
