"""Extract the immutable v158 FaceBuilder cameras and pins for identity QA.

This is inspection-only: it does not solve, move pins, or save the blend file.
Run with the v158 blend already opened in Blender background mode.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy


EXPECTED_BLEND_SHA = "7818ae012098fab814cec4f493c612b3f0cba76527d560ab8b039c9f74cb340c"


def digest_v176(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def extract_pin_records_v176() -> dict:
    from keentools.addon_config import fb_settings
    from keentools.facebuilder.fbloader import FBLoader

    source = Path(bpy.data.filepath).resolve()
    actual_sha = digest_v176(source)
    if actual_sha != EXPECTED_BLEND_SHA:
        raise RuntimeError(
            f"v158 FaceBuilder workspace checksum differs: {actual_sha}"
        )
    settings = fb_settings()
    if len(settings.heads) != 1:
        raise RuntimeError(f"expected one FaceBuilder head, found {len(settings.heads)}")
    head = settings.get_head(0)
    FBLoader.load_model(0)
    builder = FBLoader.get_builder()
    cameras = []
    for camera_index, camera in enumerate(head.cameras):
        keyframe = camera.get_keyframe()
        pins = []
        for pin_index in range(builder.pins_count(keyframe)):
            pin = builder.pin(keyframe, pin_index)
            surface = pin.surface_point
            pins.append({
                "pinIndex": pin_index,
                "imagePosition": [round(float(value), 6) for value in pin.img_pos],
                "surfacePoint": {
                    "vertexIndices": [int(value) for value in surface.geo_point_idxs],
                    "barycentricCoordinates": [
                        round(float(value), 6) for value in surface.barycentric_coordinates
                    ],
                },
            })
        projection_width, projection_height = FBLoader.size_from_projection(keyframe)
        image = camera.cam_image
        image_path = Path(image.filepath).resolve() if image else None
        cameras.append({
            "cameraIndex": camera_index,
            "keyframe": keyframe,
            "imagePath": str(image_path) if image_path else None,
            "imageSha256": digest_v176(image_path) if image_path and image_path.is_file() else None,
            "imageSize": list(image.size[:]) if image else None,
            "projectionSize": [float(projection_width), float(projection_height)],
            "focalMm": round(float(camera.focal), 6),
            "autoFocalEstimation": bool(camera.auto_focal_estimation),
            "pinCount": len(pins),
            "pins": pins,
        })
    return {
        "schemaVersion": 1,
        "iteration": "v176",
        "source": {"path": str(source), "sha256": actual_sha},
        "state": "inspection-only-no-asset-mutation",
        "headObject": head.headobj.name,
        "cameraCount": len(cameras),
        "cameras": cameras,
        "automaticApproval": False,
    }


def main_v176() -> int:
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(values)
    output = args.output.resolve()
    if output.exists():
        raise RuntimeError(f"refusing to overwrite: {output}")
    payload = extract_pin_records_v176()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "cameraCount": payload["cameraCount"],
        "pinCounts": [camera["pinCount"] for camera in payload["cameras"]],
        "state": payload["state"],
    }))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main_v176())
    except RuntimeError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(2)
