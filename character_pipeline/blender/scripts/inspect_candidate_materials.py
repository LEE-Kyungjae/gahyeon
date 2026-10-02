"""Print polygon/material membership for a candidate blend."""

import json

import bpy


for obj in [item for item in bpy.context.scene.objects if item.type == "MESH"]:
    counts = {}
    for polygon in obj.data.polygons:
        material = (
            obj.data.materials[polygon.material_index]
            if polygon.material_index < len(obj.data.materials)
            else None
        )
        name = material.name if material else "<none>"
        counts[name] = counts.get(name, 0) + 1
    print(json.dumps({
        "object": obj.name,
        "vertices": len(obj.data.vertices),
        "polygons": len(obj.data.polygons),
        "materials": counts,
        "vertexGroups": [group.name for group in obj.vertex_groups],
    }, sort_keys=True))
