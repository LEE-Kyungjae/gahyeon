"""Capture Ururu's idle, explanation, and narration motions."""
from pathlib import Path
import sys
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path: sys.path.insert(0, str(SCRIPT_DIR))
import capture_hayley_segmented_spawned_v439 as capture
capture.ITERATION = "v593"
capture.MAP = "/Game/LivingCharacterPOC/v593/QA/L_UruruConversationLibrary_v593"
capture.MESH = "/Game/LivingCharacterPOC/v585/Characters/UruruCentimeterNormalized/Ururu_CentimeterNormalized_v584"
capture.SOURCE_SCALE = 1.0
capture.EVALUATE_BEFORE_FREEZE = True
capture.LIGHT_INTENSITY_SCALE = 3.0
capture.EXPOSURE_BIAS = 0.9
capture.ANIMATIONS = (
    ("active-idle", "/Game/LivingCharacterPOC/v588/Animation/Ururu/AS_Ururu_CyberIdle_v466_v588"),
    ("explain", "/Game/LivingCharacterPOC/v588/Animation/Ururu/AS_Ururu_HandsForward_v451_v588"),
    ("narration", "/Game/LivingCharacterPOC/v588/Animation/Ururu/AS_Ururu_Narration_v472_v588"),
)
capture.OUTPUT = Path("/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v593-ururu-conversation-library-evidence")
capture.capture_hayley_segmented_spawned_v439()
