"""Inspect source and Diana torso/neck/head deform hierarchies without mutation."""

import json
from pathlib import Path

import unreal


MESHES = {
    "source": (
        "/Game/Gahyeon/CharacterPipeline/v244/AssembledMedium/"
        "Gahyeon_AnimationPOC_v244/Body/"
        "SKM_MHC_Skotukeda_SweaterJeansHightop_v243_BodyMesh"
    ),
    "diana": "/Game/Gahyeon/Character2/Diana/v024/Source/SK_Diana_CM_v024",
}
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v373-diana-neck-head-hierarchy/report.json"
)
KEYWORDS = ("pelvis", "hip", "spine", "neck", "head")


def transform_record(value):
    rotation = value.rotation.rotator()
    return {
        "translation": [round(value.translation.x, 5), round(value.translation.y, 5), round(value.translation.z, 5)],
        "rotation": [round(rotation.roll, 5), round(rotation.pitch, 5), round(rotation.yaw, 5)],
        "scale": [round(value.scale3d.x, 5), round(value.scale3d.y, 5), round(value.scale3d.z, 5)],
    }


def inspect_mesh(path):
    mesh = unreal.load_asset(path)
    if mesh is None:
        raise RuntimeError(f"mesh unavailable: {path}")
    modifier = unreal.SkeletonModifier()
    if not modifier.set_skeletal_mesh(mesh):
        raise RuntimeError(f"could not inspect skeleton: {path}")
    names = [str(value) for value in modifier.get_all_bone_names()]
    selected = [name for name in names if any(word in name.lower() for word in KEYWORDS)]
    return {
        "mesh": path,
        "boneCount": len(names),
        "bones": [
            {
                "name": name,
                "parent": str(modifier.get_parent_name(name)),
                "children": [str(value) for value in modifier.get_children_names(name, False)],
                "local": transform_record(modifier.get_bone_transform(name, False)),
                "global": transform_record(modifier.get_bone_transform(name, True)),
            }
            for name in selected
        ],
    }


report = {
    "schemaVersion": 1,
    "iteration": "v373",
    "status": "read-only-neck-head-hierarchy-inspection",
    "skeletons": {name: inspect_mesh(path) for name, path in MESHES.items()},
    "mutatedAssets": [],
    "humanApproved": False,
    "productionReady": False,
}
OUTPUT.parent.mkdir(parents=True, exist_ok=False)
OUTPUT.write_text(json.dumps(report, indent=2) + "\n")
unreal.log("DIANA_V373_NECK_HEAD_HIERARCHY=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
