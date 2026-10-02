#!/usr/bin/env python3
"""Render color-ID evidence for Ururu's disconnected native head components."""

from __future__ import annotations

import argparse
import colorsys
import hashlib
import json
from collections import deque
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--head", default="head.")
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(values)


def connected_components(mesh: bpy.types.Mesh) -> list[list[int]]:
    adjacency = [[] for _ in mesh.vertices]
    for edge in mesh.edges:
        left, right = edge.vertices
        adjacency[left].append(right)
        adjacency[right].append(left)
    unseen = set(range(len(mesh.vertices)))
    result = []
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
        result.append(sorted(component))
    return sorted(result, key=len, reverse=True)


def color_for_rank(rank: int) -> tuple[float, float, float, float]:
    if rank == 1:
        return (0.28, 0.3, 0.34, 1.0)
    hue = ((rank - 2) * 0.61803398875) % 1.0
    red, green, blue = colorsys.hsv_to_rgb(hue, 0.72, 0.95)
    return (red, green, blue, 1.0)


def build_component_objects(head: bpy.types.Object) -> list[dict]:
    reports = []
    components = connected_components(head.data)
    for rank, indices in enumerate(components, start=1):
        index_set = set(indices)
        remap = {source_index: output_index for output_index, source_index in enumerate(indices)}
        vertices = [tuple(head.data.vertices[index].co) for index in indices]
        faces = [
            tuple(remap[index] for index in polygon.vertices)
            for polygon in head.data.polygons
            if all(index in index_set for index in polygon.vertices)
        ]
        mesh = bpy.data.meshes.new(f"UruruComponent_{rank:03d}_Mesh")
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        obj = bpy.data.objects.new(f"UruruComponent_{rank:03d}", mesh)
        bpy.context.scene.collection.objects.link(obj)
        obj.matrix_world = head.matrix_world.copy()
        obj.color = color_for_rank(rank)
        reports.append(
            {
                "rank": rank,
                "object": obj.name,
                "vertexCount": len(vertices),
                "polygonCount": len(faces),
                "rgba": list(obj.color),
            }
        )
    return reports


def render_view(camera: bpy.types.Object, center: Vector, span: float, direction: Vector, path: Path) -> None:
    camera.location = center + direction.normalized() * span * 3.0
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = span * 1.12
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def main() -> None:
    args = parse_args()
    source = args.source.resolve()
    output_dir = args.output_dir.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite immutable output: {output_dir}")
    output_dir.mkdir(parents=True)
    if Path(bpy.data.filepath).resolve() != source:
        bpy.ops.wm.open_mainfile(filepath=str(source))

    head = bpy.data.objects.get(args.head)
    if head is None or head.type != "MESH":
        raise RuntimeError(f"missing head mesh: {args.head}")
    component_reports = build_component_objects(head)
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH" and not obj.name.startswith("UruruComponent_"):
            obj.hide_render = True

    points = [head.matrix_world @ vertex.co for vertex in head.data.vertices]
    minimum = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
    maximum = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
    center = (minimum + maximum) * 0.5
    span = max(maximum.x - minimum.x, maximum.z - minimum.z)

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.studio_light = "paint.sl"
    scene.display.shading.color_type = "OBJECT"
    scene.display.shading.show_shadows = False
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "WORLD"
    scene.display.shading.show_specular_highlight = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 1200
    scene.render.resolution_percentage = 100

    camera_data = bpy.data.cameras.new("UruruComponentIdCamera_v679")
    camera = bpy.data.objects.new("UruruComponentIdCamera_v679", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    renders = []
    for name, direction in (
        ("front", Vector((0, -1, 0))),
        ("left-45", Vector((-1, -1, 0))),
        ("right-45", Vector((1, -1, 0))),
        ("left-profile", Vector((-1, 0, 0))),
    ):
        path = output_dir / f"{name}.png"
        render_view(camera, center, span, direction, path)
        renders.append({"view": name, "file": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})

    report = {
        "schemaVersion": 1,
        "iteration": "v679",
        "status": "rendered-component-id-diagnostic",
        "source": str(source),
        "sourceSha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "componentCount": len(component_reports),
        "components": component_reports,
        "renders": renders,
        "decision": "diagnostic-only; visual component-role classification required before deformation",
        "automaticApproval": False,
        "humanApproved": False,
        "productionReady": False,
    }
    (output_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"iteration": "v679", "componentCount": len(component_reports), "renderCount": len(renders)}))


if __name__ == "__main__":
    main()
