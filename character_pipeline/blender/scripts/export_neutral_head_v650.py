"""Export a source character's evaluated neutral head as an immutable conform target."""

import argparse
import hashlib
import json
from pathlib import Path

import bpy
from mathutils import Vector


def sha256_v650(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evaluated_v650_bounds(obj):
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return {
        "minimum": [min(point[index] for point in points) for index in range(3)],
        "maximum": [max(point[index] for point in points) for index in range(3)],
    }


def export_v650_neutral_head():
    parser = argparse.ArgumentParser()
    parser.add_argument("--character", required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--head-object", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    argv = __import__("sys").argv
    args = parser.parse_args(argv[argv.index("--") + 1:])
    source = args.source.resolve()
    if Path(bpy.data.filepath).resolve() != source:
        raise RuntimeError(f"opened BLEND does not match requested source: {bpy.data.filepath}")
    if args.output.exists() or args.report.exists():
        raise RuntimeError("refusing to overwrite immutable v650 output")
    source_head = bpy.data.objects.get(args.head_object)
    if not source_head or source_head.type != "MESH":
        raise RuntimeError(f"missing head mesh: {args.head_object}")
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = source_head.evaluated_get(depsgraph)
    mesh = bpy.data.meshes.new_from_object(
        evaluated,
        preserve_all_data_layers=True,
        depsgraph=depsgraph,
    )
    head = bpy.data.objects.new(f"{args.character}_NeutralHead_v650", mesh)
    bpy.context.scene.collection.objects.link(head)
    head.matrix_world = source_head.matrix_world.copy()
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    head.select_set(True)
    bpy.context.view_layer.objects.active = head
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.obj_export(
        filepath=str(args.output.resolve()),
        export_selected_objects=True,
        apply_modifiers=False,
        export_materials=False,
        export_uv=True,
        export_normals=True,
        forward_axis="NEGATIVE_Z",
        up_axis="Y",
        global_scale=1.0,
    )
    if not args.output.is_file() or args.output.stat().st_size == 0:
        raise RuntimeError("neutral head OBJ export failed")
    report = {
        "schemaVersion": 1,
        "iteration": "v650",
        "status": "neutral-head-conform-input-exported",
        "character": args.character,
        "source": str(source),
        "sourceSha256": sha256_v650(source),
        "sourceHeadObject": source_head.name,
        "sourceVertexCount": len(source_head.data.vertices),
        "evaluatedVertexCount": len(mesh.vertices),
        "evaluatedPolygonCount": len(mesh.polygons),
        "worldBounds": evaluated_v650_bounds(head),
        "output": str(args.output),
        "outputBytes": args.output.stat().st_size,
        "outputSha256": sha256_v650(args.output),
        "usage": "shape reference and MetaHuman conform input only; not a final facial topology",
        "humanApproved": False,
        "releaseEligible": False,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


export_v650_neutral_head()
