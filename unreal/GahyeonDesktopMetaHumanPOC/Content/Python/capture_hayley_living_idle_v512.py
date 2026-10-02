"""Capture three fixed full-body phases of the combined Hayley living-idle draft."""

from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import capture_hayley_segmented_spawned_v439 as capture


capture.ITERATION = "v512"
capture.MAP = "/Game/LivingCharacterPOC/v512/QA/L_HayleyLivingIdle_v512"
capture.MESH = "/Game/LivingCharacterPOC/v448/Characters/HayleyBindClean/Hayley_BindPoseClean_v447"
capture.SOURCE_SCALE = 1.0
capture.EVALUATE_BEFORE_FREEZE = True
capture.ANIMATIONS = (
    ("living-idle", "/Game/LivingCharacterPOC/v511/Animation/Hayley_LivingIdle_v509"),
)
capture.OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v512-hayley-living-idle-ue-evidence"
)


def capture_hayley_living_idle_v512():
    capture.capture_hayley_segmented_spawned_v439()


capture_hayley_living_idle_v512()
