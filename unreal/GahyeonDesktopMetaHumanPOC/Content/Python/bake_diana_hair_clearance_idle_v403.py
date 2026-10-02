"""Bake restrained secondary motion and jacket clearance into Diana's approved idle."""

import json
import math
from pathlib import Path

import unreal


SOURCE = "/Game/Gahyeon/Character2/Diana/v375/Animation/AS_Diana_Idle_v244_ComponentCopy_v375"
OUTPUT = "/Game/Gahyeon/Character2/Diana/v403/Animation/AS_Diana_Idle_HairClearance_v403"
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v403-diana-hair-clearance-idle/report.json"
)

# The scalp roots stay untouched. Bias begins at the first lower segment so the
# hairline cannot detach, while long cards are curved away from the jacket.
PROFILES = {
    "R_HairChain_01": (0.0, -2.0, -2.8, 0.75, 0.1),
    "R_HairChain_02": (0.0, -1.0, -2.2, 1.10, 0.4),
    "L_HairChain_01": (0.0, 2.0, -2.8, 0.75, 0.6),
    "L_HairChain_02": (0.0, 1.0, -2.2, 1.10, 0.9),
    "R_BackHairChain_01": (-4.5, -1.0, 0.0, 0.65, 0.2),
    "R_BackHairChain_02": (-3.0, -0.7, 0.0, 0.95, 0.5),
    "C_BackHairChain_01": (-5.5, 0.0, 0.0, 0.55, 0.35),
    "C_BackHairChain_02": (-3.5, 0.0, 0.0, 0.85, 0.7),
    "L_BackHairChain_01": (-4.5, 1.0, 0.0, 0.65, 0.8),
    "L_BackHairChain_02": (-3.0, 0.7, 0.0, 0.95, 0.05),
}

if unreal.EditorAssetLibrary.does_asset_exist(OUTPUT) or REPORT.exists():
    raise RuntimeError("refusing to overwrite immutable Diana v403 hair candidate")
source = unreal.load_asset(SOURCE)
if source is None:
    raise RuntimeError(f"approved Diana idle unavailable: {SOURCE}")
target = unreal.EditorAssetLibrary.duplicate_asset(SOURCE, OUTPUT)
if target is None:
    raise RuntimeError("failed to duplicate approved Diana idle")
frame_count = int(unreal.AnimationLibrary.get_num_frames(target))
controller = target.get_editor_property("controller")
controller.open_bracket("Bake restrained Diana hair clearance and secondary motion", False)
try:
    for bone, (roll_bias, pitch_bias, yaw_bias, amplitude, phase) in PROFILES.items():
        positions = []
        rotations = []
        scales = []
        for frame in range(frame_count):
            base = unreal.AnimationLibrary.get_bone_pose_for_frame(source, bone, frame, False)
            cycle = (frame / max(1, frame_count - 1)) * math.tau
            sway = math.sin(cycle + phase * math.tau) * amplitude
            counter_sway = math.sin(cycle * 0.5 + phase * math.tau) * amplitude * 0.35
            delta = unreal.Rotator(
                pitch_bias + counter_sway,
                yaw_bias + sway,
                roll_bias + sway * 0.3,
            )
            rotations.append(delta.quaternion() * base.rotation)
            positions.append(base.translation)
            scales.append(base.scale3d)
        if not controller.set_bone_track_keys(bone, positions, rotations, scales, False):
            raise RuntimeError(f"failed to set Diana hair track: {bone}")
finally:
    controller.close_bracket(False)
if not unreal.EditorAssetLibrary.save_loaded_asset(target, False):
    raise RuntimeError("failed to save Diana v403 hair animation")

report = {
    "schemaVersion": 1,
    "iteration": "v403-diana-hair-clearance-idle",
    "status": "candidate",
    "source": SOURCE,
    "animation": OUTPUT,
    "frameCount": frame_count,
    "method": "scalp-anchored lower-chain clearance bias plus low-amplitude phase-offset secondary motion",
    "hairRootsPreserved": ["R_HairChain_00", "L_HairChain_00", "R_BackHairChain_00", "C_BackHairChain_00", "L_BackHairChain_00"],
    "drivenSegments": list(PROFILES),
    "maxSecondaryAmplitudeDegrees": max(value[3] for value in PROFILES.values()),
    "hypothesis": "Curving only lower hair segments away from the torso removes jacket penetration without detaching the scalp, while restrained phase offsets avoid rigid-card motion.",
    "actualResult": "structurally validated; desktop motion and silhouette validation pending",
    "productionReady": False,
}
REPORT.parent.mkdir(parents=True, exist_ok=False)
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("DIANA_HAIR_CLEARANCE_IDLE_V403=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
