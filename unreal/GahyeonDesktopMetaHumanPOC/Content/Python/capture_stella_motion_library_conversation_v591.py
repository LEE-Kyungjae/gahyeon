"""Capture Stella's idle, explanation, and narration motions."""
from pathlib import Path
import sys
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path: sys.path.insert(0, str(SCRIPT_DIR))
import capture_hayley_segmented_spawned_v439 as capture
capture.ITERATION = "v591"
capture.MAP = "/Game/LivingCharacterPOC/v591/QA/L_StellaConversationLibrary_v591"
capture.MESH = "/Game/LivingCharacterPOC/v572/Characters/StellaCentimeterNormalized/StellaLily_CentimeterNormalized_v571"
capture.SOURCE_SCALE = 1.0
capture.EVALUATE_BEFORE_FREEZE = True
capture.LIGHT_INTENSITY_SCALE = 3.0
capture.EXPOSURE_BIAS = 0.9
capture.ANIMATIONS = (
    ("active-idle", "/Game/LivingCharacterPOC/v588/Animation/Stella/AS_Stella_CyberIdle_v466_v588"),
    ("explain", "/Game/LivingCharacterPOC/v588/Animation/Stella/AS_Stella_HandsForward_v451_v588"),
    ("narration", "/Game/LivingCharacterPOC/v588/Animation/Stella/AS_Stella_Narration_v472_v588"),
)
capture.OUTPUT = Path("/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v591-stella-conversation-library-evidence")
capture.capture_hayley_segmented_spawned_v439()
