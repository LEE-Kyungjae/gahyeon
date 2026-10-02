"""Normalize and audit a temporary AI reconstruction mesh in Blender.

This never claims production topology and never overwrites an output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree


def parse_args() -> argparse.Namespace:
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--target-height-cm", type=float, default=172.0)
    parser.add_argument("--merge-distance-cm", type=float, default=0.001)
    parser.add_argument("--forward", choices=("-Y", "+Y", "-Z", "+Z"), default="-Y")
    parser.add_argument("--up", choices=("+Z", "+Y"), default="+Z")
    return parser.parse_args(values)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def import_mesh(path: Path) -> None:
    suffix = path.suffix.lower()
    if suffix == ".obj":
        bpy.ops.wm.obj_import(filepath=str(path))
    elif suffix in {".glb", ".gltf"}:
        bpy.ops.import_scene.gltf(filepath=str(path))
    elif suffix == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(path))
    elif suffix == ".blend":
        bpy.ops.wm.open_mainfile(filepath=str(path))
    else:
        raise SystemExit(f"unsupported reconstruction format: {suffix}")


def mesh_stats(obj) -> dict:
    mesh = obj.data
    edge_faces = [0] * len(mesh.edges)
    lookup = {tuple(sorted(edge.vertices)): edge.index for edge in mesh.edges}
    for polygon in mesh.polygons:
        vertices = polygon.vertices
        for index in range(len(vertices)):
            key = tuple(sorted((vertices[index], vertices[(index + 1) % len(vertices)])))
            edge_faces[lookup[key]] += 1
    boundary = sum(count == 1 for count in edge_faces)
    non_manifold = sum(count != 2 for count in edge_faces)
    loose = sum(count == 0 for count in edge_faces)
    return {
        "vertices": len(mesh.vertices), "edges": len(mesh.edges),
        "polygons": len(mesh.polygons), "boundaryEdges": boundary,
        "nonManifoldEdges": non_manifold, "looseEdges": loose,
    }


def world_bounds(objects) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    return (Vector(tuple(min(point[i] for point in points) for i in range(3))),
            Vector(tuple(max(point[i] for point in points) for i in range(3))))


def axis_vector(axis: str) -> Vector:
    sign = -1.0 if axis.startswith("-") else 1.0
    values = {"X": (1.0, 0.0, 0.0), "Y": (0.0, 1.0, 0.0), "Z": (0.0, 0.0, 1.0)}
    return Vector(values[axis[-1]]) * sign


def canonical_rotation(forward: str, up: str) -> Matrix:
    source_forward = axis_vector(forward)
    source_up = axis_vector(up)
    if abs(source_forward.dot(source_up)) > 1e-6:
        raise SystemExit("forward and up axes must be perpendicular")
    source_right = source_forward.cross(source_up).normalized()
    source_basis = Matrix((source_right, source_forward, source_up)).transposed()
    target_forward, target_up = Vector((0.0, -1.0, 0.0)), Vector((0.0, 0.0, 1.0))
    target_right = target_forward.cross(target_up).normalized()
    target_basis = Matrix((target_right, target_forward, target_up)).transposed()
    return target_basis @ source_basis.inverted()


def symmetry_error(obj) -> dict:
    coords = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    if not coords:
        return {"sampleCount": 0, "meanNearestMirrorCm": None, "maxNearestMirrorCm": None}
    tree = KDTree(len(coords))
    for index, coordinate in enumerate(coords):
        tree.insert(coordinate, index)
    tree.balance()
    # Spatially bounded deterministic sample with logarithmic nearest-neighbour lookup.
    stride = max(1, len(coords) // 2000)
    sample = coords[::stride]
    errors = [tree.find(Vector((-point.x, point.y, point.z)))[2] for point in sample]
    return {"sampleCount": len(sample), "meanNearestMirrorCm": round(sum(errors) / len(errors), 6),
            "maxNearestMirrorCm": round(max(errors), 6)}


def main() -> int:
    args = parse_args()
    input_path, output_path, report_path = map(Path.resolve, (args.input, args.output, args.report))
    for destination in (output_path, report_path):
        if destination.exists():
            raise SystemExit(f"refusing to overwrite: {destination}")
        destination.parent.mkdir(parents=True, exist_ok=True)
    if args.target_height_cm <= 0 or args.merge_distance_cm < 0:
        raise SystemExit("normalization parameters must be non-negative")

    if input_path.suffix.lower() != ".blend":
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False)
    import_mesh(input_path)
    objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not objects:
        raise SystemExit("candidate contains no mesh")
    before = {obj.name: mesh_stats(obj) for obj in objects}

    rotation = canonical_rotation(args.forward, args.up).to_4x4()
    for obj in objects:
        obj.matrix_world = rotation @ obj.matrix_world

    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = max(objects, key=lambda obj: len(obj.data.vertices))
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    minimum, maximum = world_bounds(objects)
    height = maximum.z - minimum.z
    if height <= 1e-6:
        raise SystemExit("candidate has zero height")
    scale = args.target_height_cm / height
    for obj in objects:
        obj.scale *= scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    minimum, maximum = world_bounds(objects)
    translation = Vector((-(minimum.x + maximum.x) * 0.5,
                          -(minimum.y + maximum.y) * 0.5, -minimum.z))
    for obj in objects:
        obj.location += translation
    bpy.context.view_layer.update()

    removed = 0
    for obj in objects:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        start = len(bm.verts)
        if args.merge_distance_cm > 0:
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=args.merge_distance_cm)
        removed += start - len(bm.verts)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()

    after = {obj.name: mesh_stats(obj) for obj in objects}
    minimum, maximum = world_bounds(objects)
    primary = max(objects, key=lambda obj: len(obj.data.vertices))
    report = {
        "schemaVersion": 1,
        "claim": "normalized-temporary-shape-estimate-not-production-mesh",
        "input": {"uri": str(input_path), "bytes": input_path.stat().st_size,
                  "sha256": digest(input_path)},
        "parameters": {"targetHeightCm": args.target_height_cm,
                       "mergeDistanceCm": args.merge_distance_cm,
                       "forward": args.forward, "up": args.up},
        "before": before, "after": after, "duplicateVerticesRemoved": removed,
        "boundsCm": {"minimum": [round(v, 6) for v in minimum],
                     "maximum": [round(v, 6) for v in maximum],
                     "dimensions": [round(maximum[i] - minimum[i], 6) for i in range(3)]},
        "symmetry": symmetry_error(primary),
        "validation": {
            "grounded": abs(minimum.z) <= 0.001,
            "heightNormalized": abs((maximum.z - minimum.z) - args.target_height_cm) <= 0.01,
            "nonManifoldEdges": sum(value["nonManifoldEdges"] for value in after.values()),
            "status": "measured-not-production-approved"
        }
    }
    bpy.ops.wm.save_as_mainfile(filepath=str(output_path), check_existing=False)
    report["output"] = {"uri": str(output_path), "bytes": output_path.stat().st_size,
                        "sha256": digest(output_path)}
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
