"""Capture Ururu's IK-retargeted walk across three fixed phases."""

from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import capture_hayley_segmented_spawned_v439 as capture


capture.ITERATION = "v583"
capture.MAP = "/Game/LivingCharacterPOC/v583/QA/L_UruruIKWalk_v583"
capture.MESH = "/Game/LivingCharacterPOC/v547/Characters/UruruTextured/Ururu_Textured_v545"
capture.SOURCE_SCALE = 1.0
capture.EVALUATE_BEFORE_FREEZE = True
capture.LIGHT_INTENSITY_SCALE = 3.0
capture.EXPOSURE_BIAS = 0.9
capture.ANIMATIONS = (
    ("ik-walk", "/Game/LivingCharacterPOC/v582/Animation/AS_Ururu_IKWalk_v582"),
)
capture.OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v583-ururu-ik-walk-evidence"
)


def capture_ururu_ik_walk_v583():
    capture.capture_hayley_segmented_spawned_v439()


capture_ururu_ik_walk_v583()
