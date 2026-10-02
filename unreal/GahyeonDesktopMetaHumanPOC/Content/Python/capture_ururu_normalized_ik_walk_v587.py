"""Capture centimeter-normalized Ururu's IK walk across three fixed phases."""

from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import capture_hayley_segmented_spawned_v439 as capture


capture.ITERATION = "v587"
capture.MAP = "/Game/LivingCharacterPOC/v587/QA/L_UruruNormalizedIKWalk_v587"
capture.MESH = "/Game/LivingCharacterPOC/v585/Characters/UruruCentimeterNormalized/Ururu_CentimeterNormalized_v584"
capture.SOURCE_SCALE = 1.0
capture.EVALUATE_BEFORE_FREEZE = True
capture.LIGHT_INTENSITY_SCALE = 3.0
capture.EXPOSURE_BIAS = 0.9
capture.ANIMATIONS = (
    ("ik-walk", "/Game/LivingCharacterPOC/v586/Animation/AS_Ururu_IKWalk_v586"),
)
capture.OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v587-ururu-normalized-ik-walk-evidence"
)


def capture_ururu_normalized_ik_walk_v587():
    capture.capture_hayley_segmented_spawned_v439()


capture_ururu_normalized_ik_walk_v587()
