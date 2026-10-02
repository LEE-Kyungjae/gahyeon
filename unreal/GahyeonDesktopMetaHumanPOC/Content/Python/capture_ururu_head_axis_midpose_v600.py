"""Render one readable middle frame for each v599 head correction."""

from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import capture_hayley_segmented_spawned_v439 as capture

capture.ITERATION = "v600"
capture.MAP = "/Game/LivingCharacterPOC/v600/QA/L_UruruHeadAxisMidpose_v600"
capture.MESH = "/Game/LivingCharacterPOC/v585/Characters/UruruCentimeterNormalized/Ururu_CentimeterNormalized_v584"
capture.SOURCE_SCALE = 1.0
capture.EVALUATE_BEFORE_FREEZE = True
capture.LIGHT_INTENSITY_SCALE = 3.0
capture.EXPOSURE_BIAS = 0.9
capture.PHASE_FRACTIONS = (0.5,)
capture.CAMERA_DISTANCE = 920.0
capture.ANIMATIONS = tuple(
    (
        label,
        f"/Game/LivingCharacterPOC/v599/Animation/AS_Ururu_Head_{label}_v466_v599",
    )
    for label in (
        "pitch_pos20", "pitch_neg20", "yaw_pos20",
        "yaw_neg20", "roll_pos20", "roll_neg20",
    )
)
capture.OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/"
    "living-character-poc-v600-ururu-head-axis-midpose-evidence"
)
capture.capture_hayley_segmented_spawned_v439()
