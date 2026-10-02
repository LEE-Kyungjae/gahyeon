"""Capture Stella's gentle living idle at three phases."""
from pathlib import Path
import sys
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path: sys.path.insert(0, str(SCRIPT_DIR))
import capture_hayley_segmented_spawned_v439 as capture
capture.ITERATION = "v607"
capture.MAP = "/Game/LivingCharacterPOC/v607/QA/L_StellaLivingIdle_v607"
capture.MESH = "/Game/LivingCharacterPOC/v572/Characters/StellaCentimeterNormalized/StellaLily_CentimeterNormalized_v571"
capture.SOURCE_SCALE = 1.0
capture.EVALUATE_BEFORE_FREEZE = True
capture.LIGHT_INTENSITY_SCALE = 3.0
capture.EXPOSURE_BIAS = 0.9
capture.ANIMATIONS = (("living-idle", "/Game/LivingCharacterPOC/v606/Animation/stella/AS_Stella_LivingIdle_v606"),)
capture.OUTPUT = Path("/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v607-stella-living-idle-evidence")
capture.capture_hayley_segmented_spawned_v439()
