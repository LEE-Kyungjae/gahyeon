"""Recapture textured Ururu with balanced fixed QA lighting."""

from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import capture_hayley_segmented_spawned_v439 as capture


capture.ITERATION = "v549"
capture.MAP = "/Game/LivingCharacterPOC/v549/QA/L_UruruTexturedEmphasis_v549"
capture.MESH = "/Game/LivingCharacterPOC/v547/Characters/UruruTextured/Ururu_Textured_v545"
capture.SOURCE_SCALE = 1.0
capture.EVALUATE_BEFORE_FREEZE = True
capture.LIGHT_INTENSITY_SCALE = 3.0
capture.EXPOSURE_BIAS = 0.9
capture.ANIMATIONS = (
    ("emphasis", "/Game/LivingCharacterPOC/v541/Animation/Ururu_RelaxedUpperIdle_v539"),
)
capture.OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v549-ururu-textured-emphasis-balanced"
)


def capture_ururu_textured_emphasis_v549():
    capture.capture_hayley_segmented_spawned_v439()


capture_ururu_textured_emphasis_v549()
