"""Capture corrected Stella/Lily fixed views with explicit yaw rotation."""

from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from living_character_bind_qa_capture import (
    LivingCharacterBindQACaptureConfig,
    capture_living_character_bind,
)


CONFIG = LivingCharacterBindQACaptureConfig(
    iteration="v522",
    map_path="/Game/LivingCharacterPOC/v522/QA/L_StellaLilyPreview_v522",
    mesh_path="/Game/LivingCharacterPOC/v520/Characters/StellaLilyPreview/StellaLily_Modular_v518",
    output_dir=Path(
        "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v522-stella-lily-ue-evidence"
    ),
)

DRIVER = capture_living_character_bind(CONFIG)
