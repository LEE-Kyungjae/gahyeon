"""Run the UE 5.8 AssetData-compatible IK batch-retarget build as v565."""

from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).with_name("build_hayley_to_stella_walk_v561.py")
SPEC = importlib.util.spec_from_file_location("hayley_to_stella_ik", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load {SCRIPT}")
build = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build)

build.ITERATION = "v565"
build.DESTINATION = "/Game/LivingCharacterPOC/v565/Retarget"
build.ANIMATION_DESTINATION = "/Game/LivingCharacterPOC/v565/Animation"
build.REPORT = build.ROOT / "artifacts/living-character-poc-v565-hayley-to-stella-ik-walk/report.json"

REPORT_VALUE = build.build_hayley_to_stella_walk_v561()
print(REPORT_VALUE)
