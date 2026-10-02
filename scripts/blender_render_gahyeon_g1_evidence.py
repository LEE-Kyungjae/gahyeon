#!/usr/bin/env python3
"""Render the sealed 15-view G1 evidence set from an authored Blender scene."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

try:
    import bpy
except ImportError as error:  # pragma: no cover - Blender runtime only
    raise SystemExit("Run this script with Blender's Python runtime") from error


MODEL_COLLECTIONS = {
    "G1_MODEL_BODY", "G1_MODEL_FACE", "G1_MODEL_EYES_TEETH",
    "G1_MODEL_HAIR", "G1_MODEL_OUTFIT",
}


def parse_args() -> argparse.Namespace:
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args(values)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    args = parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    scene = bpy.context.scene
    if scene.get("gahyeon_character_id") != "gahyeon" or scene.get("gahyeon_gate") != "G1":
        raise SystemExit("Current Blender scene is not a Gahyeon G1 authoring scene")
    if scene.get("gahyeon_scene_plan_sha256") != sha256(args.plan):
        raise SystemExit("G1 scene plan does not match the authored Blender scene")

    mesh_count = sum(
        1 for collection_name in MODEL_COLLECTIONS
        if (collection := bpy.data.collections.get(collection_name)) is not None
        for obj in collection.all_objects if obj.type == "MESH"
    )
    if mesh_count == 0:
        raise SystemExit("Refusing to render G1 evidence before a model mesh exists")

    output = args.output_dir.resolve()
    if output.exists() and any(output.iterdir()):
        raise SystemExit(f"Refusing to overwrite a non-empty evidence directory: {output}")
    output.mkdir(parents=True, exist_ok=True)
    for name in ("G1_REFERENCES_CANONICAL", "G1_REFERENCES_SUPPORTING",
                 "G1_EVIDENCE_CAMERAS"):
        collection = bpy.data.collections.get(name)
        if collection is not None:
            collection.hide_render = True

    settings = plan["evidenceRender"]
    scene.render.resolution_x = settings["resolutionX"]
    scene.render.resolution_y = settings["resolutionY"]
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = settings["fileFormat"]
    scene.render.image_settings.color_mode = settings["colorMode"]
    scene.render.film_transparent = settings["transparentBackground"]

    temporary_paths = []
    try:
        for item in plan["evidenceCameras"]:
            camera = bpy.data.objects.get(item["name"])
            if (camera is None or camera.type != "CAMERA"
                    or camera.get("evidence_view") != item["view"]):
                raise SystemExit(f"Missing or changed G1 evidence camera: {item['view']}")
            target = output / f"{item['view']}.png"
            temporary = output / f".{item['view']}.png.tmp"
            scene.camera = camera
            scene.render.filepath = str(temporary)
            bpy.ops.render.render(write_still=True)
            rendered = temporary
            if not rendered.is_file() and Path(str(temporary) + ".png").is_file():
                rendered = Path(str(temporary) + ".png")
            if not rendered.is_file() or rendered.stat().st_size == 0:
                raise SystemExit(f"Blender did not produce evidence: {item['view']}")
            temporary_paths.append((rendered, target))
        for rendered, target in temporary_paths:
            os.replace(rendered, target)
        print(json.dumps({"rendered": len(plan["evidenceCameras"]),
                          "output": str(output)}, ensure_ascii=False))
    except BaseException:
        for rendered, target in temporary_paths:
            rendered.unlink(missing_ok=True)
            target.unlink(missing_ok=True)
        raise


if __name__ == "__main__":
    main()
