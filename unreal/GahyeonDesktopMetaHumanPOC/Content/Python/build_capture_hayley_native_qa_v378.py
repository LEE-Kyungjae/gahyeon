"""Capture the legible full-body Hayley native-animation comparison."""

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
    iteration="v378",
    map_path="/Game/LivingCharacterPOC/v378/QA/L_HayleyNativeCompare_v378",
    mesh_path="/Game/LivingCharacterPOC/v371/Characters/Hayley/Hayley2",
    animation_path="/Game/LivingCharacterPOC/v371/Characters/Hayley/Hayley2_Anim",
    output_dir=Path(
        "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v378-hayley-native-qa"
    ),
    source_scale=0.1,
    camera_distance_cm=650.0,
    focal_length_mm=40.0,
    exposure_bias=0.7,
)
_driver = capture_living_character_comparison(CONFIG)
