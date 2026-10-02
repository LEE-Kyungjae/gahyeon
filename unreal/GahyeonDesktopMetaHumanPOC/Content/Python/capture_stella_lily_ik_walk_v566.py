"""Capture three fixed-camera phases of Stella/Lily's official IK-retargeted walk."""

from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import capture_hayley_segmented_spawned_v439 as capture


capture.ITERATION = "v566"
capture.MAP = "/Game/LivingCharacterPOC/v566/QA/L_StellaLilyIKWalk_v566"
capture.MESH = "/Game/LivingCharacterPOC/v558/Characters/StellaLilyTextured/StellaLily_PreviewReady_v556"
capture.SOURCE_SCALE = 1.0
capture.EVALUATE_BEFORE_FREEZE = True
capture.LIGHT_INTENSITY_SCALE = 3.0
capture.EXPOSURE_BIAS = 0.9
capture.ANIMATIONS = (
    ("ik-walk", "/Game/LivingCharacterPOC/v565/Animation/AS_StellaLily_IKWalk_v565"),
)
capture.OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v566-stella-lily-ik-walk-evidence"
)


def capture_stella_lily_ik_walk_v566():
    capture.capture_hayley_segmented_spawned_v439()


capture_stella_lily_ik_walk_v566()
