"""Create a non-destructive, body-surface-conformed v048 garment POC."""

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils.bvhtree import BVHTree


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--body", required=True)
    parser.add_argument("--garment", required=True)
    parser.add_argument("--output-blend", required=True)
    parser.add_argument("--output-fbx", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--clearance-cm", type=float, default=0.6)
    parser.add_argument("--max-move-cm", type=float, default=8.0)
    parser.add_argument("--blend", type=float, default=0.88)
    return parser.parse_args(argv)


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def import_fbx(path):
    before = set(bpy.data.objects)
    bpy.ops.wm.fbx_import(filepath=str(path), use_anim=False)
    return [obj for obj in bpy.data.objects if obj not in before]


def world_bounds(obj):
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    return {
        "min": [min(getattr(point, axis) for point in points) for axis in "xyz"],
        "max": [max(getattr(point, axis) for point in points) for axis in "xyz"],
    }


def edge_topology(mesh):
    edge_uses = {}
    for polygon in mesh.polygons:
        for edge in polygon.edge_keys:
            edge_uses[edge] = edge_uses.get(edge, 0) + 1
    return {
        "boundaryEdges": sum(count == 1 for count in edge_uses.values()),
        "nonManifoldEdges": sum(count > 2 for count in edge_uses.values()),
    }


args = parse_args()
paths = [Path(args.body), Path(args.garment)]
outputs = [Path(args.output_blend), Path(args.output_fbx), Path(args.report)]
for path in paths:
    if not path.is_file():
        raise RuntimeError(f"missing conform input: {path}")
for path in outputs:
    if path.exists():
        raise RuntimeError(f"refusing to overwrite v048 output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
body_objects = import_fbx(paths[0])
garment_objects = import_fbx(paths[1])
body = next(obj for obj in body_objects if obj.type == "MESH" and obj.name.endswith("LOD0"))
garment = next(
    obj
    for obj in garment_objects
    if obj.type == "MESH" and obj.name.startswith("DG_") and not obj.name.startswith("UCX_")
)

body_world_vertices = [body.matrix_world @ vertex.co for vertex in body.data.vertices]
body_polygons = [tuple(polygon.vertices) for polygon in body.data.polygons]
surface = BVHTree.FromPolygons(body_world_vertices, body_polygons, all_triangles=False)

material_by_vertex = {vertex.index: set() for vertex in garment.data.vertices}
for polygon in garment.data.polygons:
    for vertex_index in polygon.vertices:
        material_by_vertex[vertex_index].add(polygon.material_index)

clearance = args.clearance_cm / 100.0
max_move = args.max_move_cm / 100.0
inverse = garment.matrix_world.inverted()
movements = []
per_material = {}
for vertex in garment.data.vertices:
    world = garment.matrix_world @ vertex.co
    nearest, normal, _, distance = surface.find_nearest(world)
    if nearest is None or normal is None:
        raise RuntimeError(f"no body surface match for garment vertex {vertex.index}")
    normal.normalize()
    target = nearest + normal * clearance
    delta = target - world
    raw_distance = delta.length
    if raw_distance > max_move:
        delta *= max_move / raw_distance
    move = delta * args.blend
    vertex.co = inverse @ (world + move)
    moved_cm = move.length * 100.0
    movements.append(moved_cm)
    for material_index in material_by_vertex[vertex.index]:
        per_material.setdefault(material_index, []).append(moved_cm)

garment.name = "SM_Skotukeda_DefaultGarment_Conformed_v048"
garment.data.name = f"{garment.name}_Mesh"
garment["gahyeon_iteration"] = "v048"
garment["conform_clearance_cm"] = args.clearance_cm
garment["conform_max_move_cm"] = args.max_move_cm
garment["conform_blend"] = args.blend

# Keep only the authored garment in deliverables. Source meshes remain immutable on disk.
for obj in list(bpy.data.objects):
    obj.select_set(False)
garment.hide_set(False)
garment.hide_render = False
garment.select_set(True)
bpy.context.view_layer.objects.active = garment

bpy.ops.wm.save_as_mainfile(filepath=str(Path(args.output_blend).resolve()))
bpy.ops.export_scene.fbx(
    filepath=str(Path(args.output_fbx).resolve()),
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
    "iteration": "v048",
    "status": "static-conform-poc",
    "inputs": {
        "body": {"file": str(paths[0].resolve()), "sha256": sha256(paths[0])},
        "garment": {"file": str(paths[1].resolve()), "sha256": sha256(paths[1])},
    },
    "hypothesis": "Per-vertex body-surface conform with clearance will fit closer than global scaling without broad torso and hip penetration.",
    "parameters": {
        "clearanceCm": args.clearance_cm,
        "maxMoveCm": args.max_move_cm,
        "blend": args.blend,
    },
    "mesh": {
        "name": garment.name,
        "vertices": len(garment.data.vertices),
        "polygons": len(garment.data.polygons),
        "materials": [slot.material.name if slot.material else None for slot in garment.material_slots],
        "boundsMeters": world_bounds(garment),
        **edge_topology(garment.data),
    },
    "movementCm": {
        "min": min(movements),
        "mean": sum(movements) / len(movements),
        "max": max(movements),
        "perMaterial": {
            str(index): {
                "name": garment.material_slots[index].material.name,
                "vertices": len(values),
                "mean": sum(values) / len(values),
                "max": max(values),
            }
            for index, values in per_material.items()
        },
    },
    "outputs": {
        "blend": str(Path(args.output_blend).resolve()),
        "fbx": str(Path(args.output_fbx).resolve()),
        "fbxSha256": sha256(args.output_fbx),
    },
    "limitations": [
        "Static POC only; skin weights and Chaos Cloth are not yet transferred.",
        "Visual UE render and body-intersection QA are required before retention.",
    ],
}
Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
