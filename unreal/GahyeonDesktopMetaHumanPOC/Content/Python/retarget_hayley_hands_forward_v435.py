from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hayley_segment_retarget_v435 import run_segment_retarget_v435

run_segment_retarget_v435("explain")
