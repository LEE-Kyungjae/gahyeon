"""Refine v050 garment with material-specific body clearance for v051."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils.bvhtree import BVHTree


def args():
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--body", required=True)
    parser.add_argument("--garment", required=True)
    parser.add_argument("--output-blend", required=True)
    parser.add_argument("--output-fbx", required=True)
    parser.add_argument("--report", required=True)
    return parser.parse_args(values)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def imported(path):
    before = set(bpy.data.objects)
    bpy.ops.wm.fbx_import(filepath=str(path), use_anim=False)
    return [obj for obj in bpy.data.objects if obj not in before]


config = args()
inputs = [Path(config.body), Path(config.garment)]
outputs = [Path(config.output_blend), Path(config.output_fbx), Path(config.report)]
for path in inputs:
    if not path.is_file():
        raise RuntimeError(f"missing v051 input: {path}")
for path in outputs:
    if path.exists():
        raise RuntimeError(f"refusing to overwrite v051 output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
body_objects = imported(inputs[0])
garment_objects = imported(inputs[1])
body = next(obj for obj in body_objects if obj.type == "MESH" and obj.name.endswith("LOD0"))
garment = next(
    obj
    for obj in garment_objects
    if obj.type == "MESH" and not obj.name.startswith("UCX_")
)

body_points = [body.matrix_world @ vertex.co for vertex in body.data.vertices]
body_faces = [tuple(polygon.vertices) for polygon in body.data.polygons]
surface = BVHTree.FromPolygons(body_points, body_faces, all_triangles=False)

materials = {vertex.index: set() for vertex in garment.data.vertices}
for polygon in garment.data.polygons:
    for vertex_index in polygon.vertices:
        materials[vertex_index].add(polygon.material_index)

# Shirt: 0.8 cm retains a visible cloth layer. Shorts: 1.25 cm prevents hip exposure.
clearance_by_material = {0: 0.008, 1: 0.0125}
max_move = 0.12
inverse = garment.matrix_world.inverted()
stats = {0: [], 1: []}
unresolved = 0
for vertex in garment.data.vertices:
    world = garment.matrix_world @ vertex.co
    nearest, normal, _, _ = surface.find_nearest(world)
    if nearest is None or normal is None:
        unresolved += 1
        continue
    slots = materials[vertex.index]
    material_index = 1 if 1 in slots else 0
    clearance = clearance_by_material[material_index]
    normal.normalize()
    target = nearest + normal * clearance
    delta = target - world
    if delta.length > max_move:
        delta *= max_move / delta.length
    vertex.co = inverse @ (world + delta)
    stats[material_index].append(delta.length * 100.0)

if unresolved:
    raise RuntimeError(f"v051 has {unresolved} vertices without body-surface matches")

garment.name = "SM_Skotukeda_DefaultGarment_Conformed_v051"
garment.data.name = f"{garment.name}_Mesh"
garment["gahyeon_iteration"] = "v051"
garment["shirt_clearance_cm"] = 0.8
garment["shorts_clearance_cm"] = 1.25

for obj in bpy.data.objects:
    obj.select_set(False)
garment.select_set(True)
bpy.context.view_layer.objects.active = garment
bpy.ops.wm.save_as_mainfile(filepath=str(outputs[0].resolve()))
bpy.ops.export_scene.fbx(
    filepath=str(outputs[1].resolve()),
    use_selection=True,
    object_types={"MESH"},
    use_mesh_modifiers=True,
    add_leaf_bones=False,
    bake_anim=False,
    path_mode="COPY",
    embed_textures=False,
)

report = {
    "schemaVersion": 1,
    "iteration": "v051",
    "status": "static-conform-poc",
    "hypothesis": "Full body-surface conform plus larger shorts clearance removes the v050 boxy shirt and hip exposure.",
    "inputs": {
        "body": {"file": str(inputs[0].resolve()), "sha256": digest(inputs[0])},
        "garmentV050": {"file": str(inputs[1].resolve()), "sha256": digest(inputs[1])},
    },
    "parameters": {
        "shirtClearanceCm": 0.8,
        "shortsClearanceCm": 1.25,
        "maxMoveCm": 12.0,
    },
    "mesh": {
        "vertices": len(garment.data.vertices),
        "polygons": len(garment.data.polygons),
        "materialCount": len(garment.material_slots),
    },
    "movementCm": {
        "shirt": {"mean": sum(stats[0]) / len(stats[0]), "max": max(stats[0])},
        "shorts": {"mean": sum(stats[1]) / len(stats[1]), "max": max(stats[1])},
    },
    "outputs": {
        "blend": str(outputs[0].resolve()),
        "fbx": str(outputs[1].resolve()),
        "fbxSha256": digest(outputs[1]),
    },
    "limitations": [
        "Static POC only; skin weights and Chaos Cloth are not yet transferred.",
        "Retention requires a new UE render showing no hip, torso, or sleeve penetration.",
    ],
}
outputs[2].write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
