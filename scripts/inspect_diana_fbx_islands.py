"""Inspect connected material islands in Diana's source FBX from Blender."""

import argparse
import json
from collections import defaultdict, deque
from pathlib import Path

import bpy


def component_records(mesh_object):
    mesh = mesh_object.data
    by_material = defaultdict(list)
    for polygon in mesh.polygons:
        by_material[polygon.material_index].append(polygon)
    records = []
    for material_index, polygons in sorted(by_material.items()):
        vertex_faces = defaultdict(list)
        face_by_index = {polygon.index: polygon for polygon in polygons}
        for polygon in polygons:
            for vertex_index in polygon.vertices:
                vertex_faces[vertex_index].append(polygon.index)
        remaining = set(face_by_index)
        components = []
        while remaining:
            seed = remaining.pop()
            queue = deque([seed])
            face_indices = {seed}
            vertices = set()
            while queue:
                face_index = queue.popleft()
                polygon = face_by_index[face_index]
                vertices.update(polygon.vertices)
                for vertex_index in polygon.vertices:
                    for neighbor in vertex_faces[vertex_index]:
                        if neighbor in remaining:
                            remaining.remove(neighbor)
                            face_indices.add(neighbor)
                            queue.append(neighbor)
            coords = [mesh.vertices[index].co for index in vertices]
            minimum = [min(value[axis] for value in coords) for axis in range(3)]
            maximum = [max(value[axis] for value in coords) for axis in range(3)]
            group_weights = defaultdict(float)
            weighted_vertices = 0
            for vertex_index in vertices:
                vertex = mesh.vertices[vertex_index]
                if vertex.groups:
                    weighted_vertices += 1
                for membership in vertex.groups:
                    if membership.group < len(mesh_object.vertex_groups):
                        group_weights[mesh_object.vertex_groups[membership.group].name] += membership.weight
            dominant_groups = [
                {"name": name, "weightSum": round(weight, 6)}
                for name, weight in sorted(group_weights.items(), key=lambda item: item[1], reverse=True)[:12]
            ]
            components.append({
                "faceCount": len(face_indices),
                "vertexCount": len(vertices),
                "weightedVertexCount": weighted_vertices,
                "boundsMin": [round(value, 6) for value in minimum],
                "boundsMax": [round(value, 6) for value in maximum],
                "extent": [round(maximum[i] - minimum[i], 6) for i in range(3)],
                "dominantVertexGroups": dominant_groups,
            })
        material = mesh.materials[material_index] if material_index < len(mesh.materials) else None
        records.append({
            "materialIndex": material_index,
            "materialName": material.name if material else None,
            "componentCount": len(components),
            "components": sorted(components, key=lambda item: item["faceCount"], reverse=True),
        })
    return records


def inspect_diana_fbx_islands(fbx_path, output_path):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.wm.fbx_import(filepath=str(fbx_path))
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if len(meshes) != 1:
        raise RuntimeError(f"expected one Diana mesh, found {[obj.name for obj in meshes]}")
    mesh = meshes[0]
    report = {
        "schemaVersion": 1,
        "status": "read-only-source-fbx-island-inspection",
        "source": str(fbx_path),
        "mesh": mesh.name,
        "vertexCount": len(mesh.data.vertices),
        "faceCount": len(mesh.data.polygons),
        "materials": component_records(mesh),
        "mutatedAssets": [],
        "humanApproved": False,
        "productionReady": False,
    }
    output_path.parent.mkdir(parents=True, exist_ok=False)
    output_path.write_text(json.dumps(report, indent=2) + "\n")
    print("DIANA_FBX_ISLANDS=" + json.dumps(report, sort_keys=True))


def main_diana_fbx_islands():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fbx", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args, _ = parser.parse_known_args()
    inspect_diana_fbx_islands(args.fbx.resolve(), args.output.resolve())


if __name__ == "__main__":
    main_diana_fbx_islands()
