"""Render the six immutable v596 Ururu neck-axis candidates."""

from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import capture_hayley_segmented_spawned_v439 as capture

capture.ITERATION = "v597"
capture.MAP = "/Game/LivingCharacterPOC/v597/QA/L_UruruNeckAxisSweep_v597"
capture.MESH = "/Game/LivingCharacterPOC/v585/Characters/UruruCentimeterNormalized/Ururu_CentimeterNormalized_v584"
capture.SOURCE_SCALE = 1.0
capture.EVALUATE_BEFORE_FREEZE = True
capture.LIGHT_INTENSITY_SCALE = 3.0
capture.EXPOSURE_BIAS = 0.9
capture.CAMERA_DISTANCE = 1900.0
capture.ANIMATIONS = tuple(
    (
        label,
        f"/Game/LivingCharacterPOC/v596/Animation/AS_Ururu_Neck_{label}_v466_v596",
    )
    for label in (
        "pitch_pos12", "pitch_neg12", "yaw_pos12",
        "yaw_neg12", "roll_pos12", "roll_neg12",
    )
)
capture.OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/"
    "living-character-poc-v597-ururu-neck-axis-sweep-evidence"
)
capture.capture_hayley_segmented_spawned_v439()
