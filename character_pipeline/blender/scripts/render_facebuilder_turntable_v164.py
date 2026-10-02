"""Render a deterministic eight-view neutral QA turntable for a custom head."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def parse_args_v164() -> argparse.Namespace:
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--resolution", type=int, default=768)
    return parser.parse_args(values)


def digest_v164(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def look_at_v164(obj, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def render_facebuilder_turntable_v164() -> dict:
    args = parse_args_v164()
    source = args.input.resolve()
    output = args.output_dir.resolve()
    if not source.is_file():
        raise RuntimeError(f"missing head input: {source}")
    if output.exists():
        raise RuntimeError(f"refusing to overwrite immutable output: {output}")
    if not 512 <= args.resolution <= 2048:
        raise RuntimeError("QA render resolution must be between 512 and 2048")

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.wm.obj_import(filepath=str(source))
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if len(meshes) != 1:
        raise RuntimeError(f"expected exactly one head mesh, found {len(meshes)}")
    head = meshes[0]
    for polygon in head.data.polygons:
        polygon.use_smooth = True

    material = bpy.data.materials.new("M_FaceBuilder_QA_v164")
    material.diffuse_color = (0.48, 0.29, 0.22, 1.0)
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = (0.48, 0.29, 0.22, 1.0)
    principled.inputs["Roughness"].default_value = 0.48
    principled.inputs["Specular IOR Level"].default_value = 0.32
    head.data.materials.clear()
    head.data.materials.append(material)

    points = [head.matrix_world @ Vector(corner) for corner in head.bound_box]
    minimum = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
    maximum = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
    center = (minimum + maximum) * 0.5
    dimensions = maximum - minimum

    world = bpy.context.scene.world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.055, 0.065, 0.085, 1.0)
    background.inputs["Strength"].default_value = 0.35

    def area_light(name, location, energy, size):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        obj = bpy.data.objects.new(name, data)
        bpy.context.scene.collection.objects.link(obj)
        obj.location = center + Vector(location)
        look_at_v164(obj, center)
        return obj

    radius = max(dimensions) * 2.3
    area_light("Key_v164", (-radius, -radius, radius * 0.7), 900.0, radius * 0.8)
    area_light("Fill_v164", (radius, -radius * 0.6, radius * 0.2), 500.0, radius)
    area_light("Rim_v164", (0.0, radius, radius * 0.7), 750.0, radius * 0.7)

    camera_data = bpy.data.cameras.new("C_FaceBuilder_QA_v164")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = max(dimensions.x, dimensions.z) * 1.14
    camera = bpy.data.objects.new("C_FaceBuilder_QA_v164", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    bpy.context.scene.camera = camera

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = args.resolution
    scene.render.resolution_y = args.resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.render.resolution_percentage = 100
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.render.image_settings.color_depth = "8"
    output.mkdir(parents=True, exist_ok=False)

    views = []
    distance = max(dimensions.x, dimensions.y) * 4.0
    for index, angle_degrees in enumerate(range(0, 360, 45)):
        radians = math.radians(angle_degrees)
        camera.location = center + Vector((math.sin(radians) * distance,
                                           -math.cos(radians) * distance, 0.0))
        look_at_v164(camera, center)
        path = output / f"view-{index:02d}-yaw-{angle_degrees:03d}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        views.append({
            "index": index,
            "yawDegrees": angle_degrees,
            "path": str(path),
            "sha256": digest_v164(path),
        })

    report = {
        "schemaVersion": 1,
        "iteration": "v164",
        "state": "neutral-turntable-rendered-awaiting-identity-review",
        "source": {"path": str(source), "sha256": digest_v164(source)},
        "dimensionsCm": [round(value * 100.0, 6) for value in dimensions],
        "camera": {"projection": "orthographic", "sealedYawStepDegrees": 45},
        "lighting": "neutral-three-point-fixed",
        "views": views,
        "identityApproved": False,
        "productionReady": False,
    }
    (output / "render-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return report


if __name__ == "__main__":
    render_facebuilder_turntable_v164()
