#!/usr/bin/env python3
"""Render fixed workbench evidence for candidate windows from a motion analysis report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--analysis", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args(values)


def evaluated_bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    graph = bpy.context.evaluated_depsgraph_get()
    points = []
    for obj in objects:
        evaluated = obj.evaluated_get(graph)
        points.extend(evaluated.matrix_world @ Vector(corner) for corner in evaluated.bound_box)
    return (
        Vector(tuple(min(point[index] for point in points) for index in range(3))),
        Vector(tuple(max(point[index] for point in points) for index in range(3))),
    )


def render_fbx_motion_candidates_v479(source: Path, analysis_path: Path, output_dir: Path) -> dict[str, object]:
    if not source.is_file() or not analysis_path.is_file():
        raise FileNotFoundError(f"missing source or analysis: {source}, {analysis_path}")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"refusing to overwrite immutable evidence: {output_dir}")
    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    output_dir.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(source))
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH" and len(obj.data.polygons) > 100 and not obj.hide_render]
    if not meshes:
        raise RuntimeError("donor has no renderable mesh")
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.render.resolution_x = 512
    scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    camera_data = bpy.data.cameras.new("MotionCandidateCamera_v479")
    camera = bpy.data.objects.new("MotionCandidateCamera_v479", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    renders = []
    for segment in analysis["candidateSegments"]:
        frame = int(segment["centerFrame"])
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        minimum, maximum = evaluated_bounds(meshes)
        center = (minimum + maximum) * 0.5
        span = max(maximum.x - minimum.x, maximum.z - minimum.z)
        camera.location = center + Vector((0, -1, 0)) * span * 2.4
        camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
        camera.data.type = "ORTHO"
        camera.data.ortho_scale = span * 1.15
        output = output_dir / f"{segment['id']}-frame-{frame:04d}.png"
        scene.render.filepath = str(output)
        bpy.ops.render.render(write_still=True)
        renders.append({"segment": segment["id"], "frame": frame, "file": str(output.resolve())})
    report = {
        "schemaVersion": 1, "iteration": "v479", "status": "candidate-renders-draft",
        "source": str(source.resolve()), "analysis": str(analysis_path.resolve()),
        "renders": renders, "humanApproved": False, "releaseEligible": False,
    }
    (output_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> int:
    args = parse_args()
    report = render_fbx_motion_candidates_v479(args.input, args.analysis, args.output_dir)
    print(json.dumps({"iteration": report["iteration"], "renderCount": len(report["renders"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
