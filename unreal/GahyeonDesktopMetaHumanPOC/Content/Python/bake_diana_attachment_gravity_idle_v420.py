"""Bake restrained gravity and inertial lag into Diana's dedicated sleeve bones."""

import json
import math
from pathlib import Path

import unreal


SOURCE = "/Game/Gahyeon/Character2/Diana/v408/Animation/AS_Diana_Idle_JacketClearance_v408"
OUTPUT = "/Game/Gahyeon/Character2/Diana/v420/Animation/AS_Diana_Idle_AttachmentGravity_v420"
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v420-diana-attachment-gravity-idle/report.json"
)

# Dedicated garment controls only. Body/muscle bones are deliberately excluded.
# Values are (pitch gravity bias, yaw swing amplitude, roll lag amplitude, phase).
PROFILES = {
    "L_Sleeve_TranslateOffset": (1.10, 0.32, 0.18, 0.00),
    "R_Sleeve_TranslateOffset": (1.10, 0.32, 0.18, 0.50),
    "L_Sleeve_RotateOffset": (1.65, 0.48, 0.30, 0.12),
    "R_Sleeve_RotateOffset": (1.65, 0.48, 0.30, 0.62),
}


if unreal.EditorAssetLibrary.does_asset_exist(OUTPUT) or REPORT.exists():
    raise RuntimeError("refusing to overwrite immutable Diana v420 animation")
source = unreal.load_asset(SOURCE)
if source is None:
    raise RuntimeError(f"Diana retained idle unavailable: {SOURCE}")
target = unreal.EditorAssetLibrary.duplicate_asset(SOURCE, OUTPUT)
if target is None:
    raise RuntimeError("failed to duplicate Diana retained idle")

frame_count = int(unreal.AnimationLibrary.get_num_frames(target))
controller = target.get_editor_property("controller")
controller.open_bracket("Bake Diana sleeve attachment gravity", False)
try:
    for bone, (gravity_bias, swing_amplitude, lag_amplitude, phase) in PROFILES.items():
        positions, rotations, scales = [], [], []
        for frame in range(frame_count):
            base = unreal.AnimationLibrary.get_bone_pose_for_frame(source, bone, frame, False)
            cycle = frame / max(1, frame_count - 1) * math.tau
            swing = math.sin(cycle + phase * math.tau) * swing_amplitude
            lag = math.sin(cycle * 0.5 + phase * math.tau) * lag_amplitude
            delta = unreal.Rotator(gravity_bias + lag, swing, swing * 0.35)
            positions.append(base.translation)
            rotations.append(delta.quaternion() * base.rotation)
            scales.append(base.scale3d)
        if not controller.set_bone_track_keys(bone, positions, rotations, scales, False):
            raise RuntimeError(f"failed to set Diana attachment track: {bone}")
finally:
    controller.close_bracket(False)

if not unreal.EditorAssetLibrary.save_loaded_asset(target, False):
    raise RuntimeError("failed to save Diana v420 animation")

report = {
    "schemaVersion": 1,
    "iteration": "v420-diana-attachment-gravity-idle",
    "status": "draft",
    "source": SOURCE,
    "animation": OUTPUT,
    "frameCount": frame_count,
    "method": "low-amplitude gravity bias and phase-lag baked only into four dedicated sleeve offset bones",
    "drivenBones": list(PROFILES),
    "excludedUnsafeRegions": {
        "beltAndWeapon": "no dedicated secondary bones; weights are mixed into hip, thigh, and arm deformation bones",
        "jacketBody": "shared body and muscle weights; requires separated Chaos cloth or re-rigging",
    },
    "expectedResult": "sleeve attachments settle downward and lag the living idle without body distortion",
    "actualResult": "structural bake complete; fixed-camera runtime review pending",
    "humanApproved": False,
    "productionReady": False,
}
REPORT.parent.mkdir(parents=True, exist_ok=False)
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("DIANA_ATTACHMENT_GRAVITY_V420=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
