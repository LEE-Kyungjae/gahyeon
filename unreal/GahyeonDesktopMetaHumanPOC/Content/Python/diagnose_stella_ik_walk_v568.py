"""Run Stella's real-bone IK-walk diagnostics as immutable v568."""

from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import diagnose_stella_ik_walk_v567 as diagnostic


diagnostic.ITERATION = "v568"
diagnostic.OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v568-stella-ik-walk-real-bone-diagnostics/report.json"
)
diagnostic.diagnose_stella_ik_walk_v567()
