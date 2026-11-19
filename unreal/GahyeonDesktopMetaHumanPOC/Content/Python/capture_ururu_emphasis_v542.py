"""Capture three fixed-camera UE phases of Ururu's emphasis gesture."""

from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import capture_hayley_segmented_spawned_v439 as capture


capture.ITERATION = "v542"
capture.MAP = "/Game/LivingCharacterPOC/v542/QA/L_UruruEmphasis_v542"
capture.MESH = "/Game/LivingCharacterPOC/v525/Characters/UruruPreview/Ururu_Normalized_v523"
capture.SOURCE_SCALE = 1.0
capture.EVALUATE_BEFORE_FREEZE = True
capture.LIGHT_INTENSITY_SCALE = 5.0
capture.EXPOSURE_BIAS = 1.2
capture.ANIMATIONS = (
    ("emphasis", "/Game/LivingCharacterPOC/v541/Animation/Ururu_RelaxedUpperIdle_v539"),
)
capture.OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v542-ururu-emphasis-ue-evidence"
)


def capture_ururu_emphasis_v542():
    capture.capture_hayley_segmented_spawned_v439()


capture_ururu_emphasis_v542()
