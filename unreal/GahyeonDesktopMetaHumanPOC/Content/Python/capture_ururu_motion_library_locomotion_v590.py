"""Capture Ururu's walk, run, and stand/sit library groups."""

from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import capture_hayley_segmented_spawned_v439 as capture

capture.ITERATION = "v590"
capture.MAP = "/Game/LivingCharacterPOC/v590/QA/L_UruruLocomotionLibrary_v590"
capture.MESH = "/Game/LivingCharacterPOC/v585/Characters/UruruCentimeterNormalized/Ururu_CentimeterNormalized_v584"
capture.SOURCE_SCALE = 1.0
capture.EVALUATE_BEFORE_FREEZE = True
capture.LIGHT_INTENSITY_SCALE = 3.0
capture.EXPOSURE_BIAS = 0.9
capture.ANIMATIONS = (
    ("walk", "/Game/LivingCharacterPOC/v588/Animation/Ururu/AS_Ururu_Walk_v459_v588"),
    ("run", "/Game/LivingCharacterPOC/v588/Animation/Ururu/AS_Ururu_RunLower_v462_v588"),
    ("stand-sit", "/Game/LivingCharacterPOC/v588/Animation/Ururu/AS_Ururu_StandSit_v452_v588"),
)
capture.OUTPUT = Path("/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v590-ururu-locomotion-library-evidence")
capture.capture_hayley_segmented_spawned_v439()
