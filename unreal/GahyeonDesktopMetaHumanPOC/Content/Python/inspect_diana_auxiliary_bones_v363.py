"""Read Diana's hip/thigh auxiliary hierarchy and reference transforms."""

import json
from pathlib import Path

import unreal


MESH = "/Game/Gahyeon/Character2/Diana/v024/Source/SK_Diana_CM_v024"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v363-diana-auxiliary-bone-inspection/report.json"
)


def transform_record_v363(transform):
    translation = transform.translation
    rotation = transform.rotation.rotator()
    scale = transform.scale3d
    return {
        "translation": [round(translation.x, 5), round(translation.y, 5), round(translation.z, 5)],
        "rotation": [round(rotation.roll, 5), round(rotation.pitch, 5), round(rotation.yaw, 5)],
        "scale": [round(scale.x, 5), round(scale.y, 5), round(scale.z, 5)],
    }


def inspect_diana_auxiliary_bones_v363():
    mesh = unreal.load_asset(MESH)
    if mesh is None:
        raise RuntimeError(f"Diana mesh unavailable: {MESH}")
    modifier = unreal.SkeletonModifier()
    if not modifier.set_skeletal_mesh(mesh):
        raise RuntimeError("SkeletonModifier could not inspect Diana mesh")
    all_names = [str(value) for value in modifier.get_all_bone_names()]
    keywords = ("hip", "pelvis", "thigh", "crotch", "butt", "skirt", "coat", "jacket", "strap")
    selected = sorted(name for name in all_names if any(word in name.lower() for word in keywords))
    bones = []
    for name in selected:
        bones.append({
            "name": name,
            "parent": str(modifier.get_parent_name(name)),
            "children": [str(value) for value in modifier.get_children_names(name, False)],
            "local": transform_record_v363(modifier.get_bone_transform(name, False)),
            "global": transform_record_v363(modifier.get_bone_transform(name, True)),
        })
    report = {
        "schemaVersion": 1,
        "iteration": "v363",
        "status": "read-only-auxiliary-bone-inspection",
        "mesh": MESH,
        "boneCount": len(all_names),
        "selectedBoneCount": len(bones),
        "bones": bones,
        "mutatedAssets": [],
        "humanApproved": False,
        "productionReady": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("DIANA_V363_AUX_BONES=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


inspect_diana_auxiliary_bones_v363()
