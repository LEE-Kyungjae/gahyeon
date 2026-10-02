"""Measure donor modules against anatomical regions of the exported MetaHuman body."""

import argparse
import json
import sys
from pathlib import Path

import bpy


ROLE_OBJECTS = {
    "torso": ["Cloth_Upper_Body", "Armor_Upper_Body", "Cloth_Arms"],
    "arms": ["Armor_Upper_Arm", "Armor_Lower_Arm", "Armor_Elbow_Top", "Armor_Elbow_Bot", "Armor_Shoulder_Bot"],
    "lower": ["Cloth_Lower_Body", "Cloth_Leg", "Armor_Lower_Body", "Armor_Upper_Leg", "Armor_Lower_Leg", "Armor_Knee_Top", "Armor_Knee_Bot"],
    "footwear": ["Boot", "Armor_Feet_Back", "Armor_Feet_Front_Bot", "Armor_Feet_Front_Mid", "Armor_Feet_Front_Top"],
}


def args():
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-body", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(values)


def points(objects):
    return [obj.matrix_world @ vertex.co for obj in objects for vertex in obj.data.vertices]


def bounds(values):
    return {
        "min": [min(getattr(point, axis) for point in values) for axis in "xyz"],
        "max": [max(getattr(point, axis) for point in values) for axis in "xyz"],
    }


options = args()
if options.output.exists():
    raise RuntimeError(f"refusing to overwrite measurement: {options.output}")
options.output.parent.mkdir(parents=True, exist_ok=True)
before = set(bpy.data.objects)
bpy.ops.wm.fbx_import(filepath=str(options.target_body.resolve()), use_anim=False)
target = next(obj for obj in bpy.data.objects if obj not in before and obj.type == "MESH" and obj.name.endswith("LOD0"))
target_points = points([target])
target_bounds = bounds(target_points)
z_min, z_max = target_bounds["min"][2], target_bounds["max"][2]
height = z_max - z_min

levels = {}
for name, ratio in (("ankle", 0.06), ("knee", 0.27), ("hip", 0.50), ("waist", 0.61), ("chest", 0.73), ("shoulder", 0.84), ("neck", 0.97)):
    center_z = z_min + height * ratio
    slab = [point for point in target_points if abs(point.z - center_z) <= height * 0.0125]
    levels[name] = {"ratio": ratio, "points": len(slab), "bounds": bounds(slab)}

roles = {}
for role, names in ROLE_OBJECTS.items():
    objects = [bpy.data.objects.get(name) for name in names]
    if any(obj is None for obj in objects):
        raise RuntimeError(f"missing {role} donor objects")
    role_points = points(objects)
    roles[role] = {"objects": names, "vertices": len(role_points), "bounds": bounds(role_points)}

report = {
    "schemaVersion": 1,
    "sourceBlend": str(Path(bpy.data.filepath).resolve()),
    "targetBody": str(options.target_body.resolve()),
    "target": {"bounds": target_bounds, "levels": levels},
    "donorRoles": roles,
    "diagnosis": "v056 used donor Head+Boot full-height anchors against a headless MetaHuman body mesh; one uniform scale cannot align modular anatomical regions.",
}
options.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
