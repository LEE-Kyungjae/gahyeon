#!/usr/bin/env python3
"""Export one immutable neutral head with Blender-to-Unreal axes baked by FBX."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def parse_args_v659():
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--character", required=True)
    parser.add_argument("--head-object", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    return parser.parse_args(values)


def sha256_v659(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluated_bounds_v659(obj):
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    minimum = [min(point[index] for point in points) for index in range(3)]
    maximum = [max(point[index] for point in points) for index in range(3)]
    return {
        "minimum": minimum,
        "maximum": maximum,
        "dimensions": [maximum[index] - minimum[index] for index in range(3)],
    }


def export_unreal_heads_v659():
    args = parse_args_v659()
    if not args.source.is_file():
        raise FileNotFoundError(args.source)
    if args.output.exists() or args.report.exists():
        raise RuntimeError("refusing to overwrite immutable v659 output")
    source_object = bpy.data.objects.get(args.head_object)
    if source_object is None or source_object.type != "MESH":
        raise RuntimeError(f"neutral head object unavailable: {args.head_object}")

    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = source_object.evaluated_get(depsgraph)
    mesh = bpy.data.meshes.new_from_object(
        evaluated, preserve_all_data_layers=True, depsgraph=depsgraph
    )
    head = bpy.data.objects.new(f"{args.character}_UEHead_v659", mesh)
    bpy.context.scene.collection.objects.link(head)
    head.matrix_world = source_object.matrix_world.copy()
    bounds = evaluated_bounds_v659(head)
    dimensions = bounds["dimensions"]
    if not (12.0 <= min(dimensions) and max(dimensions) <= 40.0):
        raise RuntimeError(f"implausible head dimensions before FBX export: {dimensions}")

    bpy.ops.object.select_all(action="DESELECT")
    head.select_set(True)
    bpy.context.view_layer.objects.active = head
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result = bpy.ops.export_scene.fbx(
        filepath=str(args.output.resolve()),
        use_selection=True,
        object_types={"MESH"},
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_UNITS",
        axis_forward="-Y",
        axis_up="Z",
        bake_space_transform=False,
        add_leaf_bones=False,
        bake_anim=False,
        path_mode="AUTO",
        embed_textures=False,
    )
    if "FINISHED" not in result or not args.output.is_file() or args.output.stat().st_size < 1024:
        raise RuntimeError(f"UE-axis FBX export failed: {result}")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "iteration": "v659",
                "status": "ue-axis-baked-neutral-head-exported",
                "character": args.character,
                "source": {"path": str(args.source), "sha256": sha256_v659(args.source)},
                "sourceObject": args.head_object,
                "sourceBoundsCm": bounds,
                "output": {
                    "path": str(args.output),
                    "bytes": args.output.stat().st_size,
                    "sha256": sha256_v659(args.output),
                    "axisForward": "-Y",
                    "axisUp": "Z",
                    "unitPolicy": "FBX_SCALE_UNITS",
                },
                "role": "metahuman-conform-shape-reference-only",
                "identityApproved": False,
                "productionReady": False
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )


export_unreal_heads_v659()

