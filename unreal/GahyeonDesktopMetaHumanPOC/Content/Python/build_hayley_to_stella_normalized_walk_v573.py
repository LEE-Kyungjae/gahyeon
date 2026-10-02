"""Retarget Hayley's walk to the centimeter-normalized Stella target as v573."""

from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).with_name("build_hayley_to_stella_walk_v561.py")
SPEC = importlib.util.spec_from_file_location("hayley_to_stella_ik", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load {SCRIPT}")
build = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build)

build.ITERATION = "v573"
build.DESTINATION = "/Game/LivingCharacterPOC/v573/Retarget"
build.ANIMATION_DESTINATION = "/Game/LivingCharacterPOC/v573/Animation"
build.TARGET_MESH_PATH = "/Game/LivingCharacterPOC/v572/Characters/StellaCentimeterNormalized/StellaLily_CentimeterNormalized_v571"
build.REPORT = build.ROOT / "artifacts/living-character-poc-v573-hayley-to-stella-normalized-ik-walk/report.json"

REPORT_VALUE = build.build_hayley_to_stella_walk_v561()
print(REPORT_VALUE)
