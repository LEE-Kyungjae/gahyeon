"""Build a non-overwriting FaceBuilder control candidate with fixed focal length.

The experiment isolates the camera-solve failure found in v176.  It uses five
sealed Golden Identity views and fixes every camera to one plausible portrait
focal length before automatic pin placement.  The result remains a draft.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import bpy


WORKSPACE = Path("/Users/ze/work/gahyeonbot")
SOURCE_ROOT = WORKSPACE / "artifacts/gahyeon-ch"
OUTPUT_ROOT = SOURCE_ROOT / "iterations/v177-facebuilder-common-focal"
OUTPUT_BLEND = OUTPUT_ROOT / "gahyeon-facebuilder-common-focal-v177.blend"
OUTPUT_REPORT = OUTPUT_ROOT / "build-report.json"
COMMON_FOCAL_MM = 65.0
REFERENCES = (
    (3, "front", "ChatGPT Image 2026년 8월 10일 오후 10_57_38.png",
     "84855cabf133616975e5699217af54bc00e3804ecdfe5dfb1d22bd6887dfbc99"),
    (6, "three-quarter-left", "ChatGPT Image 2026년 8월 10일 오후 10_59_24.png",
     "ea2438b34cad90ef90fc51f76bbb0311e99a6c13c4533afd91b753815f82ed40"),
    (7, "left-profile", "ChatGPT Image 2026년 8월 10일 오후 11_01_23.png",
     "cf2a0755d0a3d179ce99a5e1124ca1e1de3b1f673eda7c8536eb1f31bb4269ac"),
    (8, "right-profile", "ChatGPT Image 2026년 8월 10일 오후 11_02_27.png",
     "9080943d8611a6efd6c8dcabcf6cb23775892c8c215030c61565882f6e9e3a2e"),
    (11, "three-quarter-right", "ChatGPT Image 2026년 8월 10일 오후 11_09_33.png",
     "4149a9bf35ea69f45161b17b88d1239202ce0f49d3311ef0fb3fc943e6aca50b"),
)


def digest_v177(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def build_common_focal_facebuilder_v177() -> dict:
    if OUTPUT_ROOT.exists():
        raise RuntimeError(f"refusing to overwrite immutable iteration: {OUTPUT_ROOT}")
    records = []
    for index, view, filename, expected_sha in REFERENCES:
        path = SOURCE_ROOT / filename
        if not path.is_file() or digest_v177(path) != expected_sha:
            raise RuntimeError(f"Golden Identity lineage differs: reference {index}")
        records.append({
            "referenceIndex": index,
            "view": view,
            "path": str(path),
            "sha256": expected_sha,
        })

    from keentools.addon_config import fb_settings
    from keentools.facebuilder.fbloader import FBLoader
    from keentools.facebuilder.interface.filedialog import read_exif_to_camera
    from keentools.facebuilder.pick_operator import (
        _add_pins_to_face,
        _init_fb_detected_faces,
    )
    from keentools.utils.detect_faces import sort_detected_faces

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    if bpy.ops.keentools_fb.add_head() != {"FINISHED"}:
        raise RuntimeError("FaceBuilder head creation failed")
    settings = fb_settings()
    head = settings.get_head(settings.get_last_headnum())
    if head is None or head.headobj is None or len(settings.heads) != 1:
        raise RuntimeError("FaceBuilder did not register exactly one head")
    head.auto_focal_estimation = False
    head.focal = COMMON_FOCAL_MM
    FBLoader.load_model(0)
    builder = FBLoader.get_builder()
    builder.set_varying_focal_length_estimation()

    camera_records = []
    for record in records:
        camera = FBLoader.add_new_camera_with_image(0, record["path"])
        camera_index = head.get_last_camnum()
        keyframe = camera.get_keyframe()
        try:
            read_exif_to_camera(0, camera_index, record["path"])
        except RuntimeError:
            pass
        camera.auto_focal_estimation = False
        camera.focal = COMMON_FOCAL_MM
        builder.set_focal_length_at(
            keyframe,
            camera.get_focal_length_in_pixels_coef() * COMMON_FOCAL_MM,
        )
        FBLoader.center_geo_camera_projection(0, camera_index)
        if _init_fb_detected_faces(builder, 0, camera_index) is None:
            raise RuntimeError(f"face detector could not load reference {record['referenceIndex']}")
        detected_faces = sort_detected_faces()
        if len(detected_faces) != 1:
            raise RuntimeError(
                f"reference {record['referenceIndex']} produced {len(detected_faces)} faces"
            )
        if not _add_pins_to_face(0, camera_index, rectangle_index=0):
            raise RuntimeError(f"automatic pin solve failed: {record['referenceIndex']}")
        pin_count = builder.pins_count(keyframe)
        camera_records.append({
            **record,
            "cameraIndex": camera_index,
            "keyframe": keyframe,
            "pinCount": pin_count,
            "focalMm": float(camera.focal),
            "autoFocalEstimation": bool(camera.auto_focal_estimation),
            "autoPinsApproved": False,
        })

    # Re-assert fixed intrinsics after every view exists, then solve the shared
    # shape twice so no intermediate sparse profile estimate survives.
    for _ in range(2):
        for camera_index, camera in enumerate(head.cameras):
            camera.auto_focal_estimation = False
            camera.focal = COMMON_FOCAL_MM
            builder.set_focal_length_at(
                camera.get_keyframe(),
                camera.get_focal_length_in_pixels_coef() * COMMON_FOCAL_MM,
            )
            if not FBLoader.solve(0, camera_index):
                raise RuntimeError(f"fixed-focal shared solve failed: camera {camera_index}")
    FBLoader.update_all_camera_positions(0)
    FBLoader.save_fb_serial_and_image_pathes(0)
    for camera_record, camera in zip(camera_records, head.cameras, strict=True):
        camera_record["focalMm"] = float(camera.focal)
        if abs(camera.focal - COMMON_FOCAL_MM) > 0.001 or camera.auto_focal_estimation:
            raise RuntimeError(f"common focal invariant failed: camera {camera_record['cameraIndex']}")

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=False)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT_BLEND), check_existing=False)
    payload = {
        "schemaVersion": 1,
        "iteration": "v177",
        "status": "draft-common-focal-control-awaiting-render-review",
        "hypothesis": (
            "Fixing all cameras to one plausible portrait focal length removes the v158 "
            "profile depth distortion and yields a closer coherent Gahyeon head."
        ),
        "action": "Rebuild FaceBuilder with five Golden Identity views at fixed 65mm.",
        "expectedResult": "Improved skull depth, nose projection and jaw agreement across views.",
        "actualResult": None,
        "decision": "awaiting-fixed-camera-render",
        "tool": "KeenTools FaceBuilder 2026.3.0",
        "blender": bpy.app.version_string,
        "commonFocalMm": COMMON_FOCAL_MM,
        "workspace": {
            "path": str(OUTPUT_BLEND),
            "sha256": digest_v177(OUTPUT_BLEND),
        },
        "headObject": head.headobj.name,
        "cameras": camera_records,
        "automaticApproval": False,
        "identityCandidate": False,
        "productionReady": False,
    }
    OUTPUT_REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
    print(json.dumps({
        "iteration": "v177",
        "status": payload["status"],
        "pinCounts": [record["pinCount"] for record in camera_records],
        "focals": [record["focalMm"] for record in camera_records],
    }))
    return payload


if __name__ == "__main__":
    try:
        build_common_focal_facebuilder_v177()
    except RuntimeError as error:
        raise SystemExit(f"ERROR: {error}")
