#!/usr/bin/env python3
"""Audit Ururu's immutable native head before authoring facial controls."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, deque
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--head", default="head.")
    return parser.parse_args(_script_args())


def _script_args() -> list[str]:
    import sys

    return sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def connected_components(mesh: bpy.types.Mesh) -> list[list[int]]:
    adjacency = [[] for _ in mesh.vertices]
    for edge in mesh.edges:
        left, right = edge.vertices
        adjacency[left].append(right)
        adjacency[right].append(left)

    unseen = set(range(len(mesh.vertices)))
    components: list[list[int]] = []
    while unseen:
        seed = min(unseen)
        unseen.remove(seed)
        queue = deque([seed])
        component = []
        while queue:
            current = queue.popleft()
            component.append(current)
            for neighbor in adjacency[current]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    queue.append(neighbor)
        components.append(sorted(component))
    return sorted(components, key=len, reverse=True)


def component_report(obj: bpy.types.Object, indices: list[int], rank: int) -> dict:
    mesh = obj.data
    index_set = set(indices)
    local_points = [mesh.vertices[index].co.copy() for index in indices]
    world_points = [obj.matrix_world @ point for point in local_points]
    material_faces = Counter()
    polygon_count = 0
    for polygon in mesh.polygons:
        if all(vertex in index_set for vertex in polygon.vertices):
            polygon_count += 1
            name = (
                mesh.materials[polygon.material_index].name
                if polygon.material_index < len(mesh.materials)
                and mesh.materials[polygon.material_index]
                else f"slot-{polygon.material_index}"
            )
            material_faces[name] += 1

    def bounds(points: list[Vector]) -> dict:
        minimum = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
        maximum = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
        return {
            "min": list(minimum),
            "max": list(maximum),
            "dimensions": list(maximum - minimum),
            "center": list((minimum + maximum) * 0.5),
        }

    return {
        "rank": rank,
        "vertexCount": len(indices),
        "polygonCount": polygon_count,
        "localBounds": bounds(local_points),
        "worldBounds": bounds(world_points),
        "materialFaceCounts": dict(sorted(material_faces.items())),
        "sampleVertexIndices": indices[:20],
    }


def topology_counts(mesh: bpy.types.Mesh) -> dict:
    edge_face_counts = Counter()
    vertex_edge_counts = Counter()
    for edge in mesh.edges:
        for vertex_index in edge.vertices:
            vertex_edge_counts[vertex_index] += 1
    for polygon in mesh.polygons:
        for edge_key in polygon.edge_keys:
            edge_face_counts[tuple(sorted(edge_key))] += 1
    return {
        "boundaryEdgeCount": sum(count == 1 for count in edge_face_counts.values()),
        "nonManifoldEdgeCount": sum(count != 2 for count in edge_face_counts.values()),
        "overSharedEdgeCount": sum(count > 2 for count in edge_face_counts.values()),
        "looseVertexCount": sum(
            vertex_edge_counts[vertex.index] == 0 for vertex in mesh.vertices
        ),
    }


def main() -> None:
    args = parse_args()
    source = Path(args.source).resolve()
    output = Path(args.output).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if Path(bpy.data.filepath).resolve() != source:
        bpy.ops.wm.open_mainfile(filepath=str(source))

    head = bpy.data.objects.get(args.head)
    if head is None or head.type != "MESH":
        raise RuntimeError(f"Missing head mesh: {args.head}")

    components = connected_components(head.data)
    material_polygons = Counter()
    for polygon in head.data.polygons:
        name = (
            head.data.materials[polygon.material_index].name
            if polygon.material_index < len(head.data.materials)
            and head.data.materials[polygon.material_index]
            else f"slot-{polygon.material_index}"
        )
        material_polygons[name] += 1

    report = {
        "schemaVersion": 1,
        "iteration": "v678",
        "status": "read-only-native-face-topology-audit",
        "source": str(source),
        "sourceSha256": sha256(source),
        "blenderVersion": bpy.app.version_string,
        "head": {
            "name": head.name,
            "vertexCount": len(head.data.vertices),
            "edgeCount": len(head.data.edges),
            "polygonCount": len(head.data.polygons),
            "shapeKeys": [key.name for key in head.data.shape_keys.key_blocks]
            if head.data.shape_keys
            else [],
            "materials": [material.name if material else None for material in head.data.materials],
            "materialPolygonCounts": dict(sorted(material_polygons.items())),
            "vertexGroups": [group.name for group in head.vertex_groups],
            "componentCount": len(components),
            "topology": topology_counts(head.data),
            "components": [
                component_report(head, indices, rank)
                for rank, indices in enumerate(components, start=1)
            ],
        },
        "decision": "measurement-only; no facial actuator is authorized by this report",
        "automaticApproval": False,
        "humanApproved": False,
        "productionReady": False,
    }
    output.parent.mkdir(parents=True, exist_ok=False)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"iteration": "v678", "components": len(components), "output": str(output)}))


if __name__ == "__main__":
    main()
