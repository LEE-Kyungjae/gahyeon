#!/usr/bin/env python3
"""Render immutable fixed-camera geometry evidence from an already-open Blender character."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--iteration", default="v514")
    parser.add_argument("--color-type", choices=("MATERIAL", "TEXTURE"), default="MATERIAL")
    parser.add_argument("--render-engine", choices=("WORKBENCH", "EEVEE"), default="WORKBENCH")
    return parser.parse_args(values)


def bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    return (
        Vector(tuple(min(point[index] for point in points) for index in range(3))),
        Vector(tuple(max(point[index] for point in points) for index in range(3))),
    )


def render(camera: bpy.types.Object, center: Vector, span: float, direction: Vector, output: Path) -> None:
    camera.location = center + direction.normalized() * span * 2.5
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = span * 1.12
    bpy.context.scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)


def setup_lighting(center: Vector, height: float) -> None:
    world = bpy.context.scene.world or bpy.data.worlds.new("CharacterEvidenceWorld")
    bpy.context.scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.035, 0.045, 0.06, 1.0)
    background.inputs["Strength"].default_value = 0.35
    for name, offset, energy, size in (
        ("Key", Vector((-0.8, -1.2, 0.65)), 950.0, 1.4),
        ("Fill", Vector((0.9, -0.75, 0.35)), 620.0, 1.2),
        ("Rim", Vector((0.25, 0.9, 0.75)), 820.0, 1.0),
    ):
        data = bpy.data.lights.new(f"CharacterEvidence{name}", "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        light = bpy.data.objects.new(f"CharacterEvidence{name}", data)
        bpy.context.scene.collection.objects.link(light)
        light.location = center + offset * height
        light.rotation_euler = (center - light.location).to_track_quat("-Z", "Y").to_euler()


def render_character_candidate_v514(
    source: Path,
    output_dir: Path,
    iteration: str,
    color_type: str = "MATERIAL",
    render_engine: str = "WORKBENCH",
) -> dict[str, object]:
    if not source.is_file():
        raise FileNotFoundError(source)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"refusing to overwrite immutable evidence: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    if source.suffix.lower() == ".fbx":
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=str(source.resolve()))

    meshes = [
        obj for obj in bpy.context.scene.objects
        if obj.type == "MESH" and not obj.hide_render and len(obj.data.polygons) > 40
    ]
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    if not meshes or len(armatures) != 1:
        raise RuntimeError(f"expected visible meshes and one armature, got {len(meshes)} meshes/{len(armatures)} rigs")

    armatures[0].data.pose_position = "REST"
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    minimum, maximum = bounds(meshes)
    center = (minimum + maximum) * 0.5
    height = maximum.z - minimum.z
    width = maximum.x - minimum.x
    if not 0.8 <= height <= 2.5:
        raise RuntimeError(f"unexpected character height in meters: {height}")

    scene = bpy.context.scene
    if render_engine == "WORKBENCH":
        scene.render.engine = "BLENDER_WORKBENCH"
        scene.display.shading.light = "STUDIO"
        scene.display.shading.studio_light = "paint.sl"
        scene.display.shading.color_type = color_type
        scene.display.shading.show_shadows = True
        scene.display.shading.show_cavity = True
        scene.display.shading.cavity_type = "WORLD"
        scene.display.shading.show_specular_highlight = True
    else:
        scene.render.engine = "BLENDER_EEVEE"
        setup_lighting(center, height)
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.resolution_percentage = 100

    camera_data = bpy.data.cameras.new(f"CharacterCandidateCamera_{iteration}")
    camera = bpy.data.objects.new(f"CharacterCandidateCamera_{iteration}", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera

    renders = []
    scene.render.resolution_x = 768
    scene.render.resolution_y = 1024
    full_span = max(height, width)
    for name, direction in (
        ("full-front", Vector((0, -1, 0))),
        ("full-left45", Vector((-1, -1, 0))),
        ("full-profile", Vector((-1, 0, 0))),
        ("full-rear", Vector((0, 1, 0))),
    ):
        path = output_dir / f"{name}.png"
        render(camera, center, full_span, direction, path)
        renders.append(str(path.resolve()))

    scene.render.resolution_x = 1024
    scene.render.resolution_y = 1024
    face_center = Vector((center.x, center.y, minimum.z + height * 0.88))
    face_span = height * 0.27
    for name, direction in (
        ("face-front", Vector((0, -1, 0))),
        ("face-left45", Vector((-1, -1, 0))),
        ("face-profile", Vector((-1, 0, 0))),
    ):
        path = output_dir / f"{name}.png"
        render(camera, face_center, face_span, direction, path)
        renders.append(str(path.resolve()))

    report = {
        "schemaVersion": 1,
        "iteration": iteration,
        "status": "rendered-draft-candidate-evidence",
        "source": {
            "file": str(source.resolve()),
            "bytes": source.stat().st_size,
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        },
        "meshCount": len(meshes),
        "armature": {"name": armatures[0].name, "boneCount": len(armatures[0].data.bones)},
        "boundsMeters": {"minimum": list(minimum), "maximum": list(maximum), "height": height},
        "renders": renders,
        "workbenchColorType": color_type,
        "renderEngine": render_engine,
        "visualValidationPending": True,
        "humanApproved": False,
        "releaseEligible": False,
    }
    (output_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    args = parse_args()
    report = render_character_candidate_v514(
        args.source,
        args.output_dir,
        args.iteration,
        args.color_type,
        args.render_engine,
    )
    print(json.dumps({"iteration": report["iteration"], "renderCount": len(report["renders"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
