from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hayley_autoaligned_retarget_v440 import run_autoaligned_retarget_v440

run_autoaligned_retarget_v440("explain")
