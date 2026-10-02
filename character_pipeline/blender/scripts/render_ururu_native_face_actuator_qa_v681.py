#!/usr/bin/env python3
"""Render readable fixed-camera Workbench QA for Ururu native face actuators."""

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
    camera_data = bpy.data.cameras.new("UruruNativeFaceCamera_v681")
    camera = bpy.data.objects.new("UruruNativeFaceCamera_v681", camera_data)
    scene.collection.objects.link(camera)
    center = Vector((0.0, -0.02, 1.245))
    camera.location = Vector((0.0, -0.62, 1.245))
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 0.36
    scene.camera = camera
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.studio_light = "paint.sl"
    scene.display.shading.color_type = "TEXTURE"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "WORLD"
    scene.display.shading.show_specular_highlight = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.resolution_x = 1024
    scene.render.resolution_y = 1024
    scene.render.resolution_percentage = 100

    renders = []
    for pose, frame in (("neutral", 1), ("blink", 10), ("gaze-left", 20), ("gaze-right", 30), ("jaw-open", 40)):
        scene.frame_set(frame)
        path = output_dir / f"{pose}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        renders.append(
            {
                "pose": pose,
                "frame": frame,
                "file": str(path),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )

    report = {
        "schemaVersion": 1,
        "iteration": "v681",
        "status": "rendered-draft-native-face-actuator-qa",
        "source": str(source),
        "sourceSha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "renderProfile": {
            "engine": "BLENDER_WORKBENCH",
            "colorType": "TEXTURE",
            "resolution": [1024, 1024],
            "camera": camera.name,
        },
        "renders": renders,
        "visualValidationPending": True,
        "automaticApproval": False,
        "humanApproved": False,
        "productionReady": False,
    }
    (output_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"iteration": "v681", "renderCount": len(renders)}))


if __name__ == "__main__":
    main()
