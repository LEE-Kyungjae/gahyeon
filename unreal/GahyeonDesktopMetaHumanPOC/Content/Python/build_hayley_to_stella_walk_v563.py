"""Run the installed-API-compatible UE IK retarget build as v563."""

from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_hayley_to_stella_walk_v561 as build


build.ITERATION = "v563"
build.DESTINATION = "/Game/LivingCharacterPOC/v563/Retarget"
build.ANIMATION_DESTINATION = "/Game/LivingCharacterPOC/v563/Animation"
build.REPORT = build.ROOT / "artifacts/living-character-poc-v563-hayley-to-stella-ik-walk/report.json"


REPORT_VALUE = build.build_hayley_to_stella_walk_v561()
