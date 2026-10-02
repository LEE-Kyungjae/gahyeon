"""Capture Stella's subtle, presentation, and emphasis motions."""
from pathlib import Path
import sys
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path: sys.path.insert(0, str(SCRIPT_DIR))
import capture_hayley_segmented_spawned_v439 as capture
capture.ITERATION = "v592"
capture.MAP = "/Game/LivingCharacterPOC/v592/QA/L_StellaSocialLibrary_v592"
capture.MESH = "/Game/LivingCharacterPOC/v572/Characters/StellaCentimeterNormalized/StellaLily_CentimeterNormalized_v571"
capture.SOURCE_SCALE = 1.0
capture.EVALUATE_BEFORE_FREEZE = True
capture.LIGHT_INTENSITY_SCALE = 3.0
capture.EXPOSURE_BIAS = 0.9
capture.ANIMATIONS = (
    ("subtle", "/Game/LivingCharacterPOC/v588/Animation/Stella/AS_Stella_ButWait_subtle_v484_v588"),
    ("present", "/Game/LivingCharacterPOC/v588/Animation/Stella/AS_Stella_ButWait_present_v484_v588"),
    ("emphasis", "/Game/LivingCharacterPOC/v588/Animation/Stella/AS_Stella_ButWait_emphasis_v484_v588"),
)
capture.OUTPUT = Path("/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v592-stella-social-library-evidence")
capture.capture_hayley_segmented_spawned_v439()
