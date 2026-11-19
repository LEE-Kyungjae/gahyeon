"""Run the corrected UE IK batch-retarget build as v564."""

from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_hayley_to_stella_walk_v561 as build


build.ITERATION = "v564"
build.DESTINATION = "/Game/LivingCharacterPOC/v564/Retarget"
build.ANIMATION_DESTINATION = "/Game/LivingCharacterPOC/v564/Animation"
build.REPORT = build.ROOT / "artifacts/living-character-poc-v564-hayley-to-stella-ik-walk/report.json"


REPORT_VALUE = build.build_hayley_to_stella_walk_v561()
