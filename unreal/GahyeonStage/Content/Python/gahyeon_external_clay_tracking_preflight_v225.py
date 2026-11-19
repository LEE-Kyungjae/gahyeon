"""Track the validated v178 Blender clay image with its exact orthographic camera."""

import hashlib
import json
from pathlib import Path

import unreal


IMAGE = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v178-keentools-cloud-equal-shape/postprocess/clay-renders-attempt-003/face-front.png"
)
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v225-external-clay-tracking-preflight/report.json"
)
BLENDER_ORTHO_VERTICAL_CM = 65.31698608398438
IMAGE_WIDTH = 1440
IMAGE_HEIGHT = 2560
UNREAL_ORTHO_WIDTH_CM = BLENDER_ORTHO_VERTICAL_CM * IMAGE_WIDTH / IMAGE_HEIGHT


def external_clay_tracking_preflight_v225():
    if OUTPUT.exists():
        raise RuntimeError("refusing to overwrite immutable v225 preflight")
    if not IMAGE.is_file():
        raise RuntimeError(f"sealed v178 clay image missing: {IMAGE}")
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    image_size, pixels = unreal.PromotedFrameUtils.get_promoted_frame_as_pixel_array_from_disk(
        str(IMAGE)
    )
    if (image_size.x, image_size.y) != (IMAGE_WIDTH, IMAGE_HEIGHT):
        raise RuntimeError(f"v178 clay resolution changed: {image_size}")
    tracked = subsystem.track_face_landmarks_from_image(pixels, image_size.x, image_size.y)
    if isinstance(tracked, tuple) and len(tracked) == 1:
        tracked = tracked[0]
    if not tracked or not hasattr(tracked, "items"):
        raise RuntimeError("UE face tracker found no curves in the validated clay image")
    curve_records = []
    for name, tracking in tracked.items():
        points = tracking.get_editor_property("tracking_points")
        curve_records.append({"name": str(name), "pointCount": len(points)})
    curve_records.sort(key=lambda record: record["name"])
    if len(curve_records) < 10:
        raise RuntimeError(f"implausibly few tracked curves: {len(curve_records)}")
    payload = {
        "schemaVersion": 1,
        "iteration": "v225",
        "state": "external-clay-tracking-camera-bound-awaiting-conform",
        "image": {
            "path": str(IMAGE),
            "sha256": hashlib.sha256(IMAGE.read_bytes()).hexdigest(),
            "size": [image_size.x, image_size.y],
        },
        "camera": {
            "projectionMode": "ORTHOGRAPHIC",
            "locationCm": [0.0, 320.0, 20.0],
            "rotationDegrees": [0.0, -90.0, 0.0],
            "blenderVerticalOrthoScaleCm": BLENDER_ORTHO_VERTICAL_CM,
            "unrealOrthoWidthCm": UNREAL_ORTHO_WIDTH_CM,
            "targetYawRotationDegrees": 180.0,
        },
        "trackedCurveCount": len(curve_records),
        "curves": curve_records,
        "conformExecuted": False,
        "identityApproved": False,
        "automaticApproval": False,
        "productionReady": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v225 external clay tracking preflight complete: {OUTPUT}")
    unreal.SystemLibrary.quit_editor()


external_clay_tracking_preflight_v225()
