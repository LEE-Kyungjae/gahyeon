"""Measure the source Hayley walk across three phases as immutable v576."""

from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import diagnose_stella_ik_walk_v567 as diagnostic


diagnostic.ITERATION = "v576"
diagnostic.MESH = "/Game/LivingCharacterPOC/v448/Characters/HayleyBindClean/Hayley_BindPoseClean_v447"
diagnostic.ANIMATION = "/Game/LivingCharacterPOC/v459/Animation/AS_HayleyClean_Walk_v459"
diagnostic.TARGET_BONES = ("root", "pelvis", "lThigh", "rThigh", "lFoot", "rFoot")
diagnostic.OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v576-hayley-walk-source-diagnostics/report.json"
)
diagnostic.diagnose_stella_ik_walk_v567()
