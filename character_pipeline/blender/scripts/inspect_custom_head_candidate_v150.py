"""Inspect a coherent custom head without modifying or promoting it."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def parse_v150_arguments() -> argparse.Namespace:
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tool", choices=("keentools-facebuilder", "faceform-wrap", "manual-multiview-fit"),
                        required=True)
    parser.add_argument("--unit-centimeters", type=float, required=True,
                        help="centimeters represented by one source unit")
    return parser.parse_args(values)


def sha256_v150(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def import_head_v150(path: Path) -> None:
    suffix = path.suffix.lower()
    if suffix == ".obj":
        bpy.ops.wm.obj_import(filepath=str(path))
    elif suffix == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(path))
    elif suffix == ".ply":
        bpy.ops.wm.ply_import(filepath=str(path))
    else:
        raise RuntimeError(f"unsupported custom head format: {suffix}")


def mesh_topology_v150(obj) -> dict:
    mesh = obj.data
    edge_use = [0] * len(mesh.edges)
    lookup = {tuple(sorted(edge.vertices)): edge.index for edge in mesh.edges}
    for polygon in mesh.polygons:
        vertices = polygon.vertices
        for index, first in enumerate(vertices):
            second = vertices[(index + 1) % len(vertices)]
            edge_use[lookup[tuple(sorted((first, second)))]] += 1
    return {
        "vertices": len(mesh.vertices),
        "edges": len(mesh.edges),
        "polygons": len(mesh.polygons),
        "triangles": sum(max(0, len(polygon.vertices) - 2) for polygon in mesh.polygons),
        "boundaryEdges": sum(value == 1 for value in edge_use),
        "nonManifoldEdges": sum(value > 2 for value in edge_use),
        "looseEdges": sum(value == 0 for value in edge_use),
    }


def inspect_custom_head_candidate_v150(input_path: Path, tool: str,
                                       unit_centimeters: float) -> dict:
    if unit_centimeters <= 0:
        raise ValueError("unit scale must be positive")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    import_head_v150(input_path)
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not meshes:
        raise ValueError("custom head contains no mesh")
    topology = {obj.name: mesh_topology_v150(obj) for obj in meshes}
    total_vertices = sum(item["vertices"] for item in topology.values())
    total_triangles = sum(item["triangles"] for item in topology.values())
    if not 1000 <= total_vertices <= 2_000_000:
        raise ValueError(f"custom head vertex count outside contract: {total_vertices}")
    points = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
    minimum = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
    maximum = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
    dimensions = [(maximum[axis] - minimum[axis]) * unit_centimeters for axis in range(3)]
    suspect_names = sorted(obj.name for obj in meshes
                           if any(token in obj.name.lower() for token in
                                  ("hair", "lash", "brow", "beard", "cloth", "shirt")))
    primary = max(meshes, key=lambda obj: len(obj.data.vertices))
    return {
        "schemaVersion": 1,
        "iteration": "v150",
        "stage": "custom-head-mesh-inspection",
        "state": "measured-awaiting-human-identity-review",
        "source": {
            "path": str(input_path.resolve()),
            "sha256": sha256_v150(input_path),
            "bytes": input_path.stat().st_size,
            "format": input_path.suffix.lower().lstrip("."),
            "tool": tool,
            "unitCentimeters": unit_centimeters
        },
        "objects": topology,
        "summary": {
            "meshObjects": len(meshes),
            "totalVertices": total_vertices,
            "totalTriangles": total_triangles,
            "primaryObject": primary.name,
            "dimensionsCm": [round(value, 6) for value in dimensions],
            "suspectedHairOrClothingObjects": suspect_names,
            "nonManifoldEdges": sum(item["nonManifoldEdges"] for item in topology.values()),
            "looseEdges": sum(item["looseEdges"] for item in topology.values())
        },
        "gates": {
            "hasCoherentPrimarySurface": topology[primary.name]["vertices"] >= 1000,
            "hairGeometryAbsent": not suspect_names,
            "productionTopologyClaimed": False,
            "identityVisuallyApproved": False,
            "cameraMatchedPortraitCaptured": False
        },
        "claim": "temporary-coherent-head-shape-for-metahuman-conform-not-production-topology",
        "automaticApproval": False,
        "productionReady": False
    }


def main() -> int:
    args = parse_v150_arguments()
    input_path, output_path = args.input.resolve(), args.output.resolve()
    if output_path.exists():
        raise SystemExit(f"refusing to overwrite: {output_path}")
    report = inspect_custom_head_candidate_v150(input_path, args.tool, args.unit_centimeters)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
