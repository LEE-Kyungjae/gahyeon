"""Retarget Hayley's walk using Ururu's authoritative UE bone names as v582."""

from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).with_name("build_hayley_to_stella_walk_v561.py")
SPEC = importlib.util.spec_from_file_location("hayley_to_target_ik", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load {SCRIPT}")
build = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build)

build.ITERATION = "v582"
build.DESTINATION = "/Game/LivingCharacterPOC/v582/Retarget"
build.ANIMATION_DESTINATION = "/Game/LivingCharacterPOC/v582/Animation"
build.TARGET_MESH_PATH = "/Game/LivingCharacterPOC/v547/Characters/UruruTextured/Ururu_Textured_v545"
build.TARGET_NAME = "Ururu"
build.OUTPUT_ANIMATION_STEM = "AS_Ururu_IKWalk"
build.TARGET_BONES = {
    "root": "root",
    "pelvis": "ValveBiped_Bip01_Pelvis",
    "spineLower": "ValveBiped_Bip01_Spine",
    "spineUpper": "ValveBiped_Bip01_Spine4",
    "neck": "ValveBiped_Bip01_Neck1",
    "head": "ValveBiped_Bip01_Head1",
    "clavicleL": "ValveBiped_Bip01_L_Clavicle",
    "upperArmL": "ValveBiped_Bip01_L_UpperArm",
    "handL": "ValveBiped_Bip01_L_Hand",
    "clavicleR": "ValveBiped_Bip01_R_Clavicle",
    "upperArmR": "ValveBiped_Bip01_R_UpperArm",
    "handR": "ValveBiped_Bip01_R_Hand",
    "thighL": "ValveBiped_Bip01_L_Thigh",
    "footL": "ValveBiped_Bip01_L_Foot",
    "toeL": "ValveBiped_Bip01_L_Toe0",
    "thighR": "ValveBiped_Bip01_R_Thigh",
    "footR": "ValveBiped_Bip01_R_Foot",
    "toeR": "ValveBiped_Bip01_R_Toe0",
}
build.REPORT = build.ROOT / "artifacts/living-character-poc-v582-hayley-to-ururu-ik-walk/report.json"

REPORT_VALUE = build.build_hayley_to_stella_walk_v561()
print(REPORT_VALUE)
