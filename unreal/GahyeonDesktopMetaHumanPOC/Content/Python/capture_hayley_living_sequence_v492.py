"""Capture the v490 sequence with Desktop-safe full-body framing."""

from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import capture_hayley_living_sequence_v491 as capture


capture.ITERATION = "v492"
capture.OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v492-hayley-desktop-framing-evidence"
)
capture.CAMERA_DISTANCE_MULTIPLIER = 1.45
capture.CAMERA_FOCAL_LENGTH = 45.0


def capture_hayley_living_sequence_v492():
    capture.capture_hayley_living_sequence_v491()


capture_hayley_living_sequence_v492()
