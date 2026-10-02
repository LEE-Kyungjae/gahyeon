"""Inspect Diana's disconnected hair chains and their baked idle tracks."""

import json
from pathlib import Path

import unreal


MESH = "/Game/Gahyeon/Character2/Diana/v024/Source/SK_Diana_CM_v024"
ANIMATION = "/Game/Gahyeon/Character2/Diana/v375/Animation/AS_Diana_Idle_v244_ComponentCopy_v375"
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v401-diana-hair-chain-runtime-inspection/report.json"
)

if REPORT.exists():
    raise RuntimeError(f"refusing to overwrite immutable report: {REPORT}")
mesh = unreal.load_asset(MESH)
animation = unreal.load_asset(ANIMATION)
if mesh is None or animation is None:
    raise RuntimeError("Diana mesh or approved idle animation unavailable")
modifier = unreal.SkeletonModifier()
if not modifier.set_skeletal_mesh(mesh):
    raise RuntimeError("could not inspect Diana skeleton")
names = [str(value) for value in modifier.get_all_bone_names()]
hair_names = [name for name in names if "HairChain" in name or name == "Head_001"]
frame_count = int(unreal.AnimationLibrary.get_num_frames(animation))


def transform_record(value):
    rotation = value.rotation.rotator()
    return {
        "translation": [round(value.translation.x, 5), round(value.translation.y, 5), round(value.translation.z, 5)],
        "rotation": [round(rotation.roll, 5), round(rotation.pitch, 5), round(rotation.yaw, 5)],
    }


bones = []
for name in hair_names:
    samples = []
    for frame in sorted({0, frame_count // 4, frame_count // 2, max(0, frame_count - 1)}):
        samples.append({
            "frame": frame,
            "local": transform_record(unreal.AnimationLibrary.get_bone_pose_for_frame(animation, name, frame, False)),
            "component": transform_record(unreal.AnimationLibrary.get_bone_pose_for_frame(animation, name, frame, True)),
        })
    bones.append({
        "name": name,
        "parent": str(modifier.get_parent_name(name)),
        "referenceLocal": transform_record(modifier.get_bone_transform(name, False)),
        "referenceComponent": transform_record(modifier.get_bone_transform(name, True)),
        "samples": samples,
    })

report = {
    "schemaVersion": 1,
    "iteration": "v401-diana-hair-chain-runtime-inspection",
    "status": "read-only-complete",
    "mesh": MESH,
    "animation": ANIMATION,
    "frameCount": frame_count,
    "hairBoneCount": len(bones),
    "bones": bones,
    "productionReady": False,
}
REPORT.parent.mkdir(parents=True, exist_ok=False)
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("DIANA_HAIR_CHAIN_RUNTIME_V401=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
