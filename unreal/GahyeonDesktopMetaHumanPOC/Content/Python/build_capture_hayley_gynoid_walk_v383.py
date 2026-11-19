"""Capture Hayley with the v382 Gynoid walk retarget for deformation QA."""

from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from living_character_qa_capture import (  # noqa: E402
    LivingCharacterQACaptureConfig,
    capture_living_character_comparison,
)


CONFIG = LivingCharacterQACaptureConfig(
    iteration="v383",
    map_path="/Game/LivingCharacterPOC/v383/QA/L_HayleyGynoidWalk_v383",
    mesh_path="/Game/LivingCharacterPOC/v371/Characters/Hayley/Hayley2",
    animation_path="/Game/LivingCharacterPOC/v382/Animation/AS_Hayley_GynoidWalk_v382",
    output_dir=Path(
        "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v383-hayley-gynoid-walk-qa"
    ),
    source_scale=0.1,
    camera_distance_cm=650.0,
    focal_length_mm=40.0,
    exposure_bias=0.7,
)
_driver = capture_living_character_comparison(CONFIG)
