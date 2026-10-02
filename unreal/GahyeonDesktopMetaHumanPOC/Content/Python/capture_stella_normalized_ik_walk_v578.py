"""Capture Stella's UE 5.8 default-op IK walk across three phases."""

from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import capture_hayley_segmented_spawned_v439 as capture


capture.ITERATION = "v578"
capture.MAP = "/Game/LivingCharacterPOC/v578/QA/L_StellaNormalizedIKWalk_v578"
capture.MESH = "/Game/LivingCharacterPOC/v572/Characters/StellaCentimeterNormalized/StellaLily_CentimeterNormalized_v571"
capture.SOURCE_SCALE = 1.0
capture.EVALUATE_BEFORE_FREEZE = True
capture.LIGHT_INTENSITY_SCALE = 3.0
capture.EXPOSURE_BIAS = 0.9
capture.ANIMATIONS = (
    ("ik-walk", "/Game/LivingCharacterPOC/v577/Animation/AS_StellaLily_IKWalk_v577"),
)
capture.OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v578-stella-normalized-ik-walk-evidence"
)


def capture_stella_normalized_ik_walk_v578():
    capture.capture_hayley_segmented_spawned_v439()


capture_stella_normalized_ik_walk_v578()
