"""Capture full-body Desktop evidence with an unbound fixed QA camera."""

from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import capture_hayley_living_sequence_v491 as capture


capture.ITERATION = "v493"
capture.OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v493-hayley-unbound-camera-evidence"
)
capture.CAMERA_FOCAL_LENGTH = 45.0
capture.USE_UNBOUND_EVIDENCE_CAMERA = True


def capture_hayley_living_sequence_v493():
    capture.capture_hayley_living_sequence_v491()


capture_hayley_living_sequence_v493()
