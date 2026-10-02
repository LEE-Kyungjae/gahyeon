"""Capture textured Stella/Lily playing the validated upper-body reaction."""

from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import capture_hayley_segmented_spawned_v439 as capture


capture.ITERATION = "v559"
capture.MAP = "/Game/LivingCharacterPOC/v559/QA/L_StellaLilyTexturedReaction_v559"
capture.MESH = "/Game/LivingCharacterPOC/v558/Characters/StellaLilyTextured/StellaLily_PreviewReady_v556"
capture.SOURCE_SCALE = 1.0
capture.EVALUATE_BEFORE_FREEZE = True
capture.LIGHT_INTENSITY_SCALE = 3.0
capture.EXPOSURE_BIAS = 0.9
capture.ANIMATIONS = (
    ("engaged-reaction", "/Game/LivingCharacterPOC/v535/Animation/StellaLily_UpperIdle_v533"),
)
capture.OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v559-stella-lily-textured-reaction"
)


def capture_stella_lily_textured_reaction_v559():
    capture.capture_hayley_segmented_spawned_v439()


capture_stella_lily_textured_reaction_v559()
