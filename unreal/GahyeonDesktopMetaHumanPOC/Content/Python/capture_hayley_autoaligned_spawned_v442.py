"""Capture the auto-aligned Hayley explain and stand/sit retargets."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import capture_hayley_segmented_spawned_v439 as capture

capture.ITERATION = "v442"
capture.MAP = "/Game/LivingCharacterPOC/v442/QA/L_HayleyAutoAlignedSpawned_v442"
capture.ANIMATIONS = (
    ("explain", "/Game/LivingCharacterPOC/v440/Animation/AS_Hayley_HandsForwardAutoAligned_v440"),
    ("stand-sit", "/Game/LivingCharacterPOC/v441/Animation/AS_Hayley_StandSitAutoAligned_v441"),
)
capture.OUTPUT = Path("/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v442-hayley-autoaligned-spawned")
capture.capture_hayley_segmented_spawned_v439()
