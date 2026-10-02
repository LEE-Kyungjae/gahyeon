"""Capture Stella/Lily's UE preview import from three fixed views."""

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
    iteration="v521",
    map_path="/Game/LivingCharacterPOC/v521/QA/L_StellaLilyPreview_v521",
    mesh_path="/Game/LivingCharacterPOC/v520/Characters/StellaLilyPreview/StellaLily_Modular_v518",
    output_dir=Path(
        "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v521-stella-lily-ue-evidence"
    ),
)

DRIVER = capture_living_character_bind(CONFIG)
