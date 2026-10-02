"""Read a donor Blender scene and emit a non-mutating structural inventory."""

import json
import sys
from pathlib import Path

import bpy


def bounds(obj):
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    if not points:
        return None
    return {
        "min": [min(getattr(point, axis) for point in points) for axis in "xyz"],
        "max": [max(getattr(point, axis) for point in points) for axis in "xyz"],
    }


argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
if len(argv) != 1:
    raise SystemExit("usage: blender scene.blend --python script.py -- report.json")
output = Path(argv[0])
if output.exists():
    raise RuntimeError(f"refusing to overwrite donor scene inventory: {output}")

objects = []
for obj in sorted(bpy.data.objects, key=lambda item: item.name.lower()):
    record = {
        "name": obj.name,
        "type": obj.type,
        "parent": obj.parent.name if obj.parent else None,
        "collections": sorted(collection.name for collection in obj.users_collection),
        "modifiers": [modifier.type for modifier in obj.modifiers],
    }
    if obj.type == "MESH":
        record.update(
            {
                "vertices": len(obj.data.vertices),
                "polygons": len(obj.data.polygons),
                "materials": [
                    slot.material.name if slot.material else None
                    for slot in obj.material_slots
                ],
                "vertexGroups": len(obj.vertex_groups),
                "shapeKeys": (
                    [block.name for block in obj.data.shape_keys.key_blocks]
                    if obj.data.shape_keys
                    else []
                ),
                "worldBounds": bounds(obj),
            }
        )
    elif obj.type == "ARMATURE":
        record.update(
            {
                "bones": len(obj.data.bones),
                "deformBones": sum(bone.use_deform for bone in obj.data.bones),
            }
        )
    objects.append(record)

report = {
    "schemaVersion": 1,
    "source": bpy.data.filepath,
    "blenderVersion": bpy.app.version_string,
    "objectCount": len(objects),
    "meshCount": sum(item["type"] == "MESH" for item in objects),
    "armatureCount": sum(item["type"] == "ARMATURE" for item in objects),
    "objects": objects,
}
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(
    json.dumps(
        {
            "objectCount": report["objectCount"],
            "meshCount": report["meshCount"],
            "armatureCount": report["armatureCount"],
        },
        indent=2,
    )
)
