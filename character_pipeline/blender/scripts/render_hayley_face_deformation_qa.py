#!/usr/bin/env python3
"""Render material-independent face deformation evidence from a Hayley FBX."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def look_at_v416(camera, target):
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()


def render_hayley_face_deformation_qa(source, output_dir, frames):
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite QA directory: {output_dir}")
    output_dir.mkdir(parents=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(source))
    face = bpy.data.objects.get("Face")
    if face is None or face.type != "MESH":
        raise RuntimeError("Hayley Face mesh is unavailable")
    for item in bpy.context.scene.objects:
        if item.type == "MESH" and item != face:
            item.hide_render = True
    face.hide_set(False)
    face.hide_render = False
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.studio_light = "paint.sl"
    scene.display.shading.color_type = "SINGLE"
    scene.display.shading.single_color = (0.55, 0.58, 0.62)
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "WORLD"
    scene.display.shading.curvature_ridge_factor = 1.5
    scene.display.shading.curvature_valley_factor = 1.0
    scene.render.resolution_x = 1024
    scene.render.resolution_y = 1024
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("WORLD_HayleyFaceDeformationQA")
    scene.world.color = (0.08, 0.08, 0.08)
    camera_data = bpy.data.cameras.new("CAM_HayleyFaceDeformationQA")
    camera_data.lens = 85.0
    camera = bpy.data.objects.new(camera_data.name, camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    world_corners = [face.matrix_world @ Vector(corner) for corner in face.bound_box]
    minimum = Vector(tuple(min(point[axis] for point in world_corners) for axis in range(3)))
    maximum = Vector(tuple(max(point[axis] for point in world_corners) for axis in range(3)))
    center = (minimum + maximum) * 0.5
    face_height = maximum.z - minimum.z
    camera.location = (center.x, minimum.y - face_height * 2.0, center.z)
    look_at_v416(camera, center)
    labels = ("neutral", "open", "neutral-return")
    records = []
    for label, frame in zip(labels, frames):
        scene.frame_set(frame)
        path = output_dir / f"{label}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        records.append({
            "label": label,
            "frame": frame,
            "file": str(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
    return records


def main():
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--frames", type=int, nargs=3, default=(1, 16, 31))
    args = parser.parse_args(values)
    if args.report.exists():
        raise FileExistsError(f"refusing to overwrite report: {args.report}")
    records = render_hayley_face_deformation_qa(args.input, args.output_dir, args.frames)
    report = {
        "schemaVersion": 1,
        "status": "material-independent-face-deformation-rendered",
        "source": str(args.input.resolve()),
        "frames": records,
        "renderMode": "Blender Workbench solid Face-only",
        "humanApproved": False,
        "releaseEligible": False,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
