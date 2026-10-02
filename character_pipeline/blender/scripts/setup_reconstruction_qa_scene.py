"""Add deterministic cameras and neutral lighting to a normalized candidate scene."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector


CAMERAS = {
    "face-neutral-front": (0.0, -1.0, 0.0, 1.0),
    "face-neutral-three-quarter-left": (-1.0, -1.0, 0.0, 1.0),
    "face-neutral-three-quarter-right": (1.0, -1.0, 0.0, 1.0),
    "face-neutral-left-profile": (-1.0, 0.0, 0.0, 1.0),
    "face-neutral-right-profile": (1.0, 0.0, 0.0, 1.0),
    "body-neutral-front": (0.0, -1.0, 0.0, 0.0),
    "body-neutral-left": (-1.0, 0.0, 0.0, 0.0),
    "body-neutral-right": (1.0, 0.0, 0.0, 0.0),
    "body-neutral-rear": (0.0, 1.0, 0.0, 0.0),
}


def parse_args() -> argparse.Namespace:
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(values)


def bounds() -> tuple[Vector, Vector]:
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not meshes:
        raise SystemExit("QA scene requires at least one mesh")
    points = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
    return (
        Vector(tuple(min(point[i] for point in points) for i in range(3))),
        Vector(tuple(max(point[i] for point in points) for i in range(3))),
    )


def point_at(obj, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def configure_candidate_scene() -> dict:
    minimum, maximum = bounds()
    center = (minimum + maximum) * 0.5
    height = maximum.z - minimum.z
    width = maximum.x - minimum.x
    depth = maximum.y - minimum.y
    subject_radius = max(width, depth) * 0.5
    head_only = height < 80.0
    go_aspect = 1440.0 / 2560.0

    for obj in list(bpy.data.objects):
        if obj.type in {"CAMERA", "LIGHT"}:
            bpy.data.objects.remove(obj, do_unlink=True)

    camera_records = []
    for view, (dx, dy, dz, is_face) in CAMERAS.items():
        face_target_z = center.z if head_only else maximum.z - height * 0.095
        target = Vector((center.x, center.y, face_target_z if is_face else center.z))
        direction = Vector((dx, dy, dz)).normalized()
        distance = 320.0 if is_face else 420.0
        camera_data = bpy.data.cameras.new(f"QA_{view}")
        camera = bpy.data.objects.new(f"QA_{view}", camera_data)
        bpy.context.scene.collection.objects.link(camera)
        camera.location = target + direction * distance
        point_at(camera, target)
        camera_data.type = "ORTHO"
        if is_face and head_only:
            camera_data.ortho_scale = max(height * 1.12, width / go_aspect * 1.08)
        elif is_face:
            camera_data.ortho_scale = height * 0.27
        else:
            camera_data.ortho_scale = max(
                height * 1.08, width / go_aspect * 1.08, subject_radius * 2.12
            )
        camera_data.lens = 70.0
        camera["evidence_view"] = view
        camera["qa_protocol"] = "looking-glass-go-single-view-v1"
        camera_records.append({"view": view, "orthographicScaleCm": camera_data.ortho_scale})

    light_specs = (
        ("QA_Key", (-120.0, -150.0, maximum.z + 40.0), 1700.0, 105.0),
        ("QA_Fill", (120.0, -90.0, maximum.z - 10.0), 900.0, 120.0),
        ("QA_Rim", (0.0, 110.0, maximum.z + 30.0), 1300.0, 90.0),
    )
    for name, position, energy, size in light_specs:
        data = bpy.data.lights.new(name, "AREA")
        data.energy, data.shape, data.size = energy, "DISK", size
        obj = bpy.data.objects.new(name, data)
        bpy.context.scene.collection.objects.link(obj)
        obj.location = position
        point_at(obj, center)

    world = bpy.context.scene.world or bpy.data.worlds.new("QA_NeutralWorld")
    bpy.context.scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.18, 0.19, 0.21, 1.0)
    background.inputs["Strength"].default_value = 0.35
    scene = bpy.context.scene
    scene.render.resolution_x = 1440
    scene.render.resolution_y = 2560
    scene.render.resolution_percentage = 100
    scene.render.pixel_aspect_x = 1.0
    scene.render.pixel_aspect_y = 1.0
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 1.65
    scene["qa_display_profile"] = "looking-glass-go"
    scene["qa_panel_resolution"] = "1440x2560"
    scene["qa_quilt_view_count"] = 66
    return {
        "schemaVersion": 1,
        "protocol": "looking-glass-go-single-view-v1",
        "panelResolution": [1440, 2560],
        "quiltViewCount": 66,
        "subjectScope": "head-only" if head_only else "full-body",
        "boundsCm": {"minimum": list(minimum), "maximum": list(maximum)},
        "cameras": camera_records,
    }


def main() -> int:
    args = parse_args()
    output = args.output.resolve()
    if output.exists():
        raise SystemExit(f"refusing to overwrite: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    report = configure_candidate_scene()
    bpy.ops.wm.save_as_mainfile(filepath=str(output), check_existing=False)
    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
