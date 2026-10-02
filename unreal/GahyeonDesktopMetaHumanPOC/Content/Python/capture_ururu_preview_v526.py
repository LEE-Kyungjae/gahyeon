"""Capture Ururu's normalized UE preview from three fixed views."""

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
    iteration="v526",
    map_path="/Game/LivingCharacterPOC/v526/QA/L_UruruPreview_v526",
    mesh_path="/Game/LivingCharacterPOC/v525/Characters/UruruPreview/Ururu_Normalized_v523",
    output_dir=Path(
        "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v526-ururu-ue-evidence"
    ),
)

DRIVER = capture_living_character_bind(CONFIG)
