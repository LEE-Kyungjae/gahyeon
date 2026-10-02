"""Capture corrected Ururu gentle living idle at three phases."""
from pathlib import Path
import sys
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path: sys.path.insert(0, str(SCRIPT_DIR))
import capture_hayley_segmented_spawned_v439 as capture
capture.ITERATION = "v608"
capture.MAP = "/Game/LivingCharacterPOC/v608/QA/L_UruruLivingIdle_v608"
capture.MESH = "/Game/LivingCharacterPOC/v585/Characters/UruruCentimeterNormalized/Ururu_CentimeterNormalized_v584"
capture.SOURCE_SCALE = 1.0
capture.EVALUATE_BEFORE_FREEZE = True
capture.LIGHT_INTENSITY_SCALE = 3.0
capture.EXPOSURE_BIAS = 0.9
capture.ANIMATIONS = (("living-idle", "/Game/LivingCharacterPOC/v606/Animation/ururu/AS_Ururu_LivingIdle_Corrected_v606"),)
capture.OUTPUT = Path("/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v608-ururu-living-idle-evidence")
capture.capture_hayley_segmented_spawned_v439()
