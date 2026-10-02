"""Inspect immutable v048 body/garment FBX sources without modifying them."""

import json
import sys
from pathlib import Path

import bpy


def argv_after_separator():
    return sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []


def world_bbox(obj):
    corners = [obj.matrix_world @ v.co for v in obj.data.vertices]
    return {
        "min": [min(getattr(v, axis) for v in corners) for axis in ("x", "y", "z")],
        "max": [max(getattr(v, axis) for v in corners) for axis in ("x", "y", "z")],
    }


args = argv_after_separator()
if len(args) != 3:
    raise SystemExit("usage: blender ... -- body.fbx garment.fbx report.json")

body_path, garment_path, report_path = map(Path, args)
bpy.ops.wm.read_factory_settings(use_empty=True)

report = {"schemaVersion": 1, "sources": {}}
for role, path in (("body", body_path), ("garment", garment_path)):
    before = set(bpy.data.objects)
    bpy.ops.wm.fbx_import(filepath=str(path), use_anim=False)
    imported = [obj for obj in bpy.data.objects if obj not in before]
    meshes = [obj for obj in imported if obj.type == "MESH"]
    report["sources"][role] = {
        "file": str(path.resolve()),
        "objects": [
            {
                "name": obj.name,
                "type": obj.type,
                "parent": obj.parent.name if obj.parent else None,
                "location": list(obj.location),
                "rotationEuler": list(obj.rotation_euler),
                "scale": list(obj.scale),
                **(
                    {
                        "vertices": len(obj.data.vertices),
                        "polygons": len(obj.data.polygons),
                        "materials": [slot.material.name if slot.material else None for slot in obj.material_slots],
                        "worldBounds": world_bbox(obj),
                    }
                    if obj.type == "MESH"
                    else {}
                ),
            }
            for obj in imported
        ],
        "meshCount": len(meshes),
    }

output = Path(report_path)
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
