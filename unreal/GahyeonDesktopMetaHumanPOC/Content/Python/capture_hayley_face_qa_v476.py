"""Capture legible neutral/blink/smile evidence without face accessories."""

from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import capture_hayley_clean_expression_v470 as capture


capture.ITERATION = "v476"
capture.MESH = "/Game/LivingCharacterPOC/v475/Characters/HayleyFaceQA/Hayley_FaceQA_v474"
capture.MAP = "/Game/LivingCharacterPOC/v476/QA/L_HayleyFaceQA_v476"
capture.OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v476-hayley-face-expression-evidence"
)


def capture_hayley_face_qa_v476():
    capture.capture_hayley_clean_expression_v470()


capture_hayley_face_qa_v476()
