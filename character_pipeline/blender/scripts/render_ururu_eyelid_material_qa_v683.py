#!/usr/bin/env python3
"""Evaluate v680 eyelid material under a non-clipping Eevee profile."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(values)


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

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.resolution_x = 1024
    scene.render.resolution_y = 1024
    scene.render.resolution_percentage = 100
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = -1.25

    material = bpy.data.materials.get("Ururu_EyelidSkin_v680")
    if material is None:
        raise RuntimeError("v680 eyelid material was not found")
    material.diffuse_color = (0.33, 0.255, 0.235, 1.0)
    principled = material.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = (0.33, 0.255, 0.235, 1.0)
    principled.inputs["Roughness"].default_value = 0.62

    world = scene.world or bpy.data.worlds.new("UruruEyelidWorld_v683")
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.045, 0.05, 0.065, 1.0)
    background.inputs["Strength"].default_value = 0.12

    center = Vector((0.0, -0.02, 1.245))
    for name, location, energy, size in (
        ("Key", Vector((-0.55, -0.75, 1.65)), 35.0, 0.7),
        ("Fill", Vector((0.55, -0.6, 1.45)), 18.0, 0.65),
    ):
        light_data = bpy.data.lights.new(f"UruruEyelid{name}_v683", "AREA")
        light_data.energy = energy
        light_data.shape = "DISK"
        light_data.size = size
        light = bpy.data.objects.new(f"UruruEyelid{name}_v683", light_data)
        scene.collection.objects.link(light)
        light.location = location
        light.rotation_euler = (center - light.location).to_track_quat("-Z", "Y").to_euler()

    camera_data = bpy.data.cameras.new("UruruEyelidCamera_v683")
    camera = bpy.data.objects.new("UruruEyelidCamera_v683", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.location = Vector((0.0, -0.62, 1.245))
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 0.36

    renders = []
    for pose, frame in (("neutral", 1), ("blink", 10)):
        scene.frame_set(frame)
        path = output_dir / f"{pose}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        renders.append({"pose": pose, "frame": frame, "file": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    report = {
        "schemaVersion": 1,
        "iteration": "v683",
        "status": "rendered-eyelid-material-diagnostic",
        "source": str(source),
        "sourceSha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "exposure": scene.view_settings.exposure,
        "eyelidBaseColor": list(material.diffuse_color),
        "renders": renders,
        "visualValidationPending": True,
        "automaticApproval": False,
        "humanApproved": False,
        "productionReady": False,
    }
    (output_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"iteration": "v683", "renderCount": len(renders)}))


if __name__ == "__main__":
    main()
