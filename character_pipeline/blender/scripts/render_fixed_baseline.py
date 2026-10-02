"""Render fixed Blender QA views and emit a checksummed manifest.

Run inside Blender with an authored scene already open.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy


VIEWS = {
    "face-front": "face-neutral-front",
    "face-left-45": "face-neutral-three-quarter-left",
    "face-right-45": "face-neutral-three-quarter-right",
    "face-left-profile": "face-neutral-left-profile",
    "face-right-profile": "face-neutral-right-profile",
    "body-front": "body-neutral-front",
    "body-left": "body-neutral-left",
    "body-right": "body-neutral-right",
    "body-rear": "body-neutral-rear",
}


def digest(path: Path) -> str:
    value = hashlib.sha256(path.read_bytes()).hexdigest()
    return value


def main() -> int:
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--view", action="append", choices=tuple(VIEWS), required=True)
    parser.add_argument("--width", type=int, default=1440)
    parser.add_argument("--height", type=int, default=2560)
    parser.add_argument("--hide", action="append", default=[])
    args = parser.parse_args(values)
    output = args.output_dir.resolve()
    if output.exists() and any(output.iterdir()):
        raise SystemExit(f"refusing to overwrite baseline output: {output}")
    output.mkdir(parents=True, exist_ok=True)
    for collection_name in args.hide:
        collection = bpy.data.collections.get(collection_name)
        if collection is None:
            raise SystemExit(f"requested hidden collection is missing: {collection_name}")
        collection.hide_render = True
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    if args.width < 64 or args.height < 64:
        raise SystemExit("baseline resolution must be at least 64 pixels per axis")
    scene.render.resolution_x = args.width
    scene.render.resolution_y = args.height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    records = []
    for label in args.view:
        evidence_view = VIEWS[label]
        cameras = [item for item in bpy.data.objects
                   if item.type == "CAMERA" and item.get("evidence_view") == evidence_view]
        if len(cameras) != 1:
            raise SystemExit(f"expected one sealed camera for {evidence_view}, found {len(cameras)}")
        scene.camera = cameras[0]
        path = output / f"{label}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        records.append({"view": label, "evidenceView": evidence_view,
                        "uri": path.name, "bytes": path.stat().st_size,
                        "sha256": digest(path)})
    manifest = {
        "schemaVersion": 1,
        "renderer": "blender-fixed-baseline-v1",
        "sourceBlend": bpy.data.filepath,
        "sourceRevision": scene.get("gahyeon_model_revision"),
        "resolution": [args.width, args.height],
        "displayProfile": (
            "looking-glass-go-single-view" if [args.width, args.height] == [1440, 2560]
            else "custom-non-official"
        ),
        "engine": scene.render.engine,
        "filmTransparent": scene.render.film_transparent,
        "views": records,
    }
    (output / "render-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
