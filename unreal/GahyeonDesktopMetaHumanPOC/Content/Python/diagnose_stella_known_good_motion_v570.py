"""Measure Stella's known-visible upper-body motion for scale comparison."""

from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import diagnose_stella_ik_walk_v567 as diagnostic


diagnostic.ITERATION = "v570"
diagnostic.ANIMATION = "/Game/LivingCharacterPOC/v535/Animation/StellaLily_UpperIdle_v533"
diagnostic.OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v570-stella-known-good-motion-diagnostics/report.json"
)
diagnostic.diagnose_stella_ik_walk_v567()
