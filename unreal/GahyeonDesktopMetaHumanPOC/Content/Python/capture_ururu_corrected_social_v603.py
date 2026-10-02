"""Capture corrected Ururu reaction and presentation motions."""
from pathlib import Path
import sys
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path: sys.path.insert(0, str(SCRIPT_DIR))
import capture_hayley_segmented_spawned_v439 as capture
capture.ITERATION = "v603"
capture.MAP = "/Game/LivingCharacterPOC/v603/QA/L_UruruCorrectedSocial_v603"
capture.MESH = "/Game/LivingCharacterPOC/v585/Characters/UruruCentimeterNormalized/Ururu_CentimeterNormalized_v584"
capture.SOURCE_SCALE = 1.0
capture.EVALUATE_BEFORE_FREEZE = True
capture.LIGHT_INTENSITY_SCALE = 3.0
capture.EXPOSURE_BIAS = 0.9
capture.ANIMATIONS = (
    ("subtle-reaction", "/Game/LivingCharacterPOC/v601/Animation/Ururu/AS_Ururu_Corrected_ButWait_subtle_v484_v601"),
    ("present", "/Game/LivingCharacterPOC/v601/Animation/Ururu/AS_Ururu_Corrected_ButWait_present_v484_v601"),
    ("emphasis", "/Game/LivingCharacterPOC/v601/Animation/Ururu/AS_Ururu_Corrected_ButWait_emphasis_v484_v601"),
)
capture.OUTPUT = Path("/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v603-ururu-corrected-social-evidence")
capture.capture_hayley_segmented_spawned_v439()
