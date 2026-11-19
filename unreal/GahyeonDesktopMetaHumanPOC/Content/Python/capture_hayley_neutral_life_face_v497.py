"""Capture exact neutral, blink, and gaze frames on the accessory-free face QA mesh."""

from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import capture_hayley_clean_expression_v470 as capture


capture.ITERATION = "v497"
capture.MESH = "/Game/LivingCharacterPOC/v475/Characters/HayleyFaceQA/Hayley_FaceQA_v474"
capture.ANIMATION = "/Game/LivingCharacterPOC/v495/Animation/Hayley_NeutralLife_v494"
capture.MAP = "/Game/LivingCharacterPOC/v497/QA/L_HayleyNeutralLifeFace_v497"
capture.OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v497-hayley-neutral-life-face-evidence"
)
capture.POSES = (("neutral", 0.0), ("blink", 70.0 / 30.0), ("gaze", 118.0 / 30.0))
capture.OUTPUT_FILENAME = "hayley-neutral-blink-gaze.png"


def capture_hayley_neutral_life_face_v497():
    capture.capture_hayley_clean_expression_v470()


capture_hayley_neutral_life_face_v497()
