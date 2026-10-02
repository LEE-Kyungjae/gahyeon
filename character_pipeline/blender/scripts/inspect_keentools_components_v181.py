"""Inspect connected components inside each v178 material primitive."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import bmesh
import bpy


def inspect_keentools_components_v181() -> dict:
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(values)
    if args.output.exists():
        raise RuntimeError(f"refusing to overwrite component audit: {args.output}")
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if len(meshes) != 1:
        raise RuntimeError(f"expected one mesh, found {len(meshes)}")
    obj = meshes[0]
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    remaining = set(bm.faces)
    components = []
    while remaining:
        seed = remaining.pop()
        stack = [seed]
        faces = [seed]
        while stack:
            face = stack.pop()
            for edge in face.edges:
                for linked in edge.link_faces:
                    if linked in remaining:
                        remaining.remove(linked)
                        stack.append(linked)
                        faces.append(linked)
        vertices = {vertex for face in faces for vertex in face.verts}
        minimum = [min(vertex.co[axis] for vertex in vertices) for axis in range(3)]
        maximum = [max(vertex.co[axis] for vertex in vertices) for axis in range(3)]
        material_counts = {}
        for face in faces:
            key = str(face.material_index)
            material_counts[key] = material_counts.get(key, 0) + 1
        components.append({
            "faces": len(faces), "vertices": len(vertices),
            "materialCounts": material_counts,
            "boundsCm": {"minimum": [round(float(v), 6) for v in minimum],
                         "maximum": [round(float(v), 6) for v in maximum]},
        })
    bm.free()
    components.sort(key=lambda item: item["faces"], reverse=True)
    payload = {"schemaVersion": 1, "iteration": "v181-component-audit",
               "source": bpy.data.filepath, "components": components}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({"components": len(components), "largest": components[:10]}))
    return payload


if __name__ == "__main__":
    inspect_keentools_components_v181()
