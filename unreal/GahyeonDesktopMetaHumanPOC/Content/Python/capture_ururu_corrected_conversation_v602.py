"""Capture corrected Ururu conversation motions."""
from pathlib import Path
import sys
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path: sys.path.insert(0, str(SCRIPT_DIR))
import capture_hayley_segmented_spawned_v439 as capture
capture.ITERATION = "v602"
capture.MAP = "/Game/LivingCharacterPOC/v602/QA/L_UruruCorrectedConversation_v602"
capture.MESH = "/Game/LivingCharacterPOC/v585/Characters/UruruCentimeterNormalized/Ururu_CentimeterNormalized_v584"
capture.SOURCE_SCALE = 1.0
capture.EVALUATE_BEFORE_FREEZE = True
capture.LIGHT_INTENSITY_SCALE = 3.0
capture.EXPOSURE_BIAS = 0.9
capture.ANIMATIONS = (
    ("active-idle", "/Game/LivingCharacterPOC/v601/Animation/Ururu/AS_Ururu_Corrected_CyberIdle_v466_v601"),
    ("explain", "/Game/LivingCharacterPOC/v601/Animation/Ururu/AS_Ururu_Corrected_HandsForward_v451_v601"),
    ("narration", "/Game/LivingCharacterPOC/v601/Animation/Ururu/AS_Ururu_Corrected_Narration_v472_v601"),
)
capture.OUTPUT = Path("/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v602-ururu-corrected-conversation-evidence")
capture.capture_hayley_segmented_spawned_v439()
