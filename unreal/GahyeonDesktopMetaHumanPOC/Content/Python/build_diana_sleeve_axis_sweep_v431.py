"""Build immutable ±90-degree sleeve attachment axis candidates for Diana."""

import json
from pathlib import Path

import unreal


SOURCE = "/Game/Gahyeon/Character2/Diana/v420/Animation/AS_Diana_Idle_AttachmentGravity_v420"
OUTPUT_ROOT = "/Game/Gahyeon/Character2/Diana/v431/Animation"
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v431-diana-sleeve-axis-sweep/report.json"
)
BONES = ("L_Sleeve_RotateOffset", "R_Sleeve_RotateOffset")
CANDIDATES = {
    "pitch-pos90": unreal.Rotator(90.0, 0.0, 0.0),
    "pitch-neg90": unreal.Rotator(-90.0, 0.0, 0.0),
    "yaw-pos90": unreal.Rotator(0.0, 90.0, 0.0),
    "yaw-neg90": unreal.Rotator(0.0, -90.0, 0.0),
    "roll-pos90": unreal.Rotator(0.0, 0.0, 90.0),
    "roll-neg90": unreal.Rotator(0.0, 0.0, -90.0),
}


def build_diana_sleeve_axis_sweep_v431():
    if REPORT.exists() or unreal.EditorAssetLibrary.list_assets(OUTPUT_ROOT, recursive=True):
        raise RuntimeError("refusing to overwrite immutable Diana v431 sleeve-axis outputs")
    source = unreal.load_asset(SOURCE)
    if source is None:
        raise RuntimeError(f"missing retained attachment animation: {SOURCE}")
    frame_count = int(unreal.AnimationLibrary.get_num_frames(source))
    records = []
    for label, delta in CANDIDATES.items():
        output = f"{OUTPUT_ROOT}/AS_Diana_Idle_Sleeve_{label.replace('-', '_')}_v431"
        target = unreal.EditorAssetLibrary.duplicate_asset(SOURCE, output)
        if target is None:
            raise RuntimeError(f"failed to duplicate sleeve-axis candidate: {label}")
        controller = target.get_editor_property("controller")
        controller.open_bracket(f"Diana sleeve axis {label}", False)
        try:
            for bone in BONES:
                positions, rotations, scales = [], [], []
                for frame in range(frame_count):
                    base = unreal.AnimationLibrary.get_bone_pose_for_frame(source, bone, frame, False)
                    positions.append(base.translation)
                    rotations.append(delta.quaternion() * base.rotation)
                    scales.append(base.scale3d)
                if not controller.set_bone_track_keys(bone, positions, rotations, scales, False):
                    raise RuntimeError(f"{label}: failed to write {bone}")
        finally:
            controller.close_bracket(False)
        if not unreal.EditorAssetLibrary.save_loaded_asset(target, only_if_is_dirty=False):
            raise RuntimeError(f"failed to save sleeve-axis candidate: {output}")
        records.append({
            "label": label,
            "animation": output,
            "deltaRotatorDegrees": {
                "pitch": delta.pitch,
                "yaw": delta.yaw,
                "roll": delta.roll,
            },
            "drivenBones": list(BONES),
        })
    report = {
        "schemaVersion": 1,
        "iteration": "v431",
        "status": "draft-six-axis-sleeve-orientation-sweep",
        "source": SOURCE,
        "frameCount": frame_count,
        "hypothesis": "The rigid horizontal rods are sleeve attachments with a 90-degree local RotateOffset orientation error.",
        "candidates": records,
        "visualValidationPending": True,
        "humanApproved": False,
        "productionReady": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.log("DIANA_SLEEVE_AXIS_SWEEP_V431=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


build_diana_sleeve_axis_sweep_v431()
