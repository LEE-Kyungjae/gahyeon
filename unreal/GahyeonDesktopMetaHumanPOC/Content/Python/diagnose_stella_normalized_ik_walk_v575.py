"""Measure normalized Stella's IK-walk translations and rotations as v575."""

from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import diagnose_stella_ik_walk_v567 as diagnostic


diagnostic.ITERATION = "v575"
diagnostic.MESH = "/Game/LivingCharacterPOC/v572/Characters/StellaCentimeterNormalized/StellaLily_CentimeterNormalized_v571"
diagnostic.ANIMATION = "/Game/LivingCharacterPOC/v573/Animation/AS_StellaLily_IKWalk_v573"
diagnostic.OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v575-stella-normalized-ik-walk-diagnostics/report.json"
)
diagnostic.diagnose_stella_ik_walk_v567()
