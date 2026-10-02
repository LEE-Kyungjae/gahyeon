from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hayley_motion_presets import run_hayley_motion_preset

run_hayley_motion_preset("hands-forward-v429")
