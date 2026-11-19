"""Bake a stronger scalp-anchored jacket-clearance profile for Diana's card hair."""

import json
import math
from pathlib import Path

import unreal


SOURCE = "/Game/Gahyeon/Character2/Diana/v375/Animation/AS_Diana_Idle_v244_ComponentCopy_v375"
OUTPUT = "/Game/Gahyeon/Character2/Diana/v408/Animation/AS_Diana_Idle_JacketClearance_v408"
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v408-diana-jacket-clearance-idle/report.json"
)
# (roll bias, pitch bias, yaw bias, secondary amplitude, phase)
# Roots (_00) remain untouched; the first and second lower segments form a
# clearance arc over Diana's voluminous jacket instead of moving the scalp.
PROFILES = {
    "R_HairChain_01": (-5.0, -4.0, -6.5, 1.0, 0.10),
    "R_HairChain_02": (-4.0, -2.5, -4.0, 1.4, 0.35),
    "L_HairChain_01": (-5.0, 4.0, 6.5, 1.0, 0.60),
    "L_HairChain_02": (-4.0, 2.5, 4.0, 1.4, 0.85),
    "R_BackHairChain_01": (-11.0, -2.5, -2.0, 0.9, 0.20),
    "R_BackHairChain_02": (-7.0, -1.5, -1.0, 1.3, 0.45),
    "C_BackHairChain_01": (-13.0, 0.0, 0.0, 0.8, 0.35),
    "C_BackHairChain_02": (-8.0, 0.0, 0.0, 1.2, 0.65),
    "L_BackHairChain_01": (-11.0, 2.5, 2.0, 0.9, 0.75),
    "L_BackHairChain_02": (-7.0, 1.5, 1.0, 1.3, 0.05),
}

if unreal.EditorAssetLibrary.does_asset_exist(OUTPUT) or REPORT.exists():
    raise RuntimeError("refusing to overwrite immutable Diana v408 animation")
source = unreal.load_asset(SOURCE)
if source is None:
    raise RuntimeError(f"approved Diana idle unavailable: {SOURCE}")
target = unreal.EditorAssetLibrary.duplicate_asset(SOURCE, OUTPUT)
if target is None:
    raise RuntimeError("failed to duplicate approved Diana idle")
frame_count = int(unreal.AnimationLibrary.get_num_frames(target))
controller = target.get_editor_property("controller")
controller.open_bracket("Bake Diana jacket-clearance hair arc", False)
try:
    for bone, (roll_bias, pitch_bias, yaw_bias, amplitude, phase) in PROFILES.items():
        positions, rotations, scales = [], [], []
        for frame in range(frame_count):
            base = unreal.AnimationLibrary.get_bone_pose_for_frame(source, bone, frame, False)
            cycle = frame / max(1, frame_count - 1) * math.tau
            sway = math.sin(cycle + phase * math.tau) * amplitude
            lag = math.sin(cycle * 0.5 + phase * math.tau) * amplitude * 0.3
            delta = unreal.Rotator(
                pitch_bias + lag,
                yaw_bias + sway,
                roll_bias + sway * 0.25,
            )
            positions.append(base.translation)
            rotations.append(delta.quaternion() * base.rotation)
            scales.append(base.scale3d)
        if not controller.set_bone_track_keys(bone, positions, rotations, scales, False):
            raise RuntimeError(f"failed to set Diana hair track: {bone}")
finally:
    controller.close_bracket(False)
if not unreal.EditorAssetLibrary.save_loaded_asset(target, False):
    raise RuntimeError("failed to save Diana v408 animation")

report = {
    "schemaVersion": 1,
    "iteration": "v408-diana-jacket-clearance-idle",
    "status": "candidate",
    "source": SOURCE,
    "animation": OUTPUT,
    "frameCount": frame_count,
    "method": "preserve five scalp roots; arc ten lower chain segments over the jacket with restrained phase lag",
    "drivenSegments": list(PROFILES),
    "maximumStaticBiasDegrees": 13.0,
    "maximumSecondaryAmplitudeDegrees": 1.4,
    "expectedResult": "front and rear long cards remain outside the jacket volume during idle without scalp detachment",
    "actualResult": "structurally validated; desktop silhouette review pending",
    "humanApproved": False,
    "productionReady": False
}
REPORT.parent.mkdir(parents=True, exist_ok=False)
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("DIANA_JACKET_CLEARANCE_IDLE_V408=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
