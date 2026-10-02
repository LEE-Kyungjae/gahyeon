"""Capture three UE phases of Stella/Lily's foot-locked upper-body idle."""

from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import capture_hayley_segmented_spawned_v439 as capture


capture.ITERATION = "v536"
capture.MAP = "/Game/LivingCharacterPOC/v536/QA/L_StellaLilyUpperIdle_v536"
capture.MESH = "/Game/LivingCharacterPOC/v520/Characters/StellaLilyPreview/StellaLily_Modular_v518"
capture.SOURCE_SCALE = 1.0
capture.EVALUATE_BEFORE_FREEZE = True
capture.LIGHT_INTENSITY_SCALE = 5.0
capture.EXPOSURE_BIAS = 1.2
capture.ANIMATIONS = (
    ("upper-idle", "/Game/LivingCharacterPOC/v535/Animation/StellaLily_UpperIdle_v533"),
)
capture.OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v536-stella-lily-upper-idle-ue-evidence"
)


def capture_stella_lily_upper_idle_v536():
    capture.capture_hayley_segmented_spawned_v439()


capture_stella_lily_upper_idle_v536()
