"""Create a non-overwriting FaceBuilder auto-fit from canonical identity views.

Run only after the user has accepted the KeenTools EULA, installed Core, and
activated the FaceBuilder trial/license. This script performs the mechanical
single-face detection and initial solve; it does not approve pins or claim
that the resulting head matches the identity.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import bpy


OUTPUT_BLEND = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v158-facebuilder-canonical-autofit/gahyeon-facebuilder-autofit-v158.blend"
)
OUTPUT_REPORT = OUTPUT_BLEND.with_name("autofit-report.json")
REFERENCES = (
    (3, "front", "ChatGPT Image 2026년 8월 10일 오후 10_57_38.png",
     "84855cabf133616975e5699217af54bc00e3804ecdfe5dfb1d22bd6887dfbc99"),
    (6, "three-quarter", "ChatGPT Image 2026년 8월 10일 오후 10_59_24.png",
     "ea2438b34cad90ef90fc51f76bbb0311e99a6c13c4533afd91b753815f82ed40"),
    (7, "left-profile", "ChatGPT Image 2026년 8월 10일 오후 11_01_23.png",
     "cf2a0755d0a3d179ce99a5e1124ca1e1de3b1f673eda7c8536eb1f31bb4269ac"),
    (8, "right-profile", "ChatGPT Image 2026년 8월 10일 오후 11_02_27.png",
     "9080943d8611a6efd6c8dcabcf6cb23775892c8c215030c61565882f6e9e3a2e"),
)
REFERENCE_ROOT = Path("/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch")


def digest_v158(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def verify_reference_lineage_v158() -> list[dict]:
    records = []
    for index, view, filename, expected in REFERENCES:
        source = REFERENCE_ROOT / filename
        if not source.is_file() or digest_v158(source) != expected:
            raise RuntimeError(f"canonical reference lineage differs: {index}")
        records.append({"index": index, "view": view, "path": str(source),
                        "sha256": expected})
    return records


def bootstrap_facebuilder_workspace_v158() -> dict:
    if OUTPUT_BLEND.exists() or OUTPUT_REPORT.exists():
        raise RuntimeError("refusing to overwrite immutable v158 workspace")
    references = verify_reference_lineage_v158()
    addon = bpy.context.preferences.addons.get("keentools")
    if addon is None:
        raise RuntimeError("KeenTools add-on is not enabled")

    # Importing these modules proves that the installed add-on registered its
    # FaceBuilder surface. Creating the head then proves Core and a license are
    # available; the operator fails closed otherwise.
    from keentools.addon_config import fb_settings
    from keentools.facebuilder.fbloader import FBLoader
    from keentools.facebuilder.interface.filedialog import (
        auto_setup_camera_from_exif,
        read_exif_to_camera,
    )
    from keentools.facebuilder.pick_operator import (
        _add_pins_to_face,
        _init_fb_detected_faces,
    )
    from keentools.utils.detect_faces import sort_detected_faces

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    result = bpy.ops.keentools_fb.add_head()
    if result != {"FINISHED"}:
        raise RuntimeError(f"FaceBuilder head creation failed: {result}")
    settings = fb_settings()
    headnum = settings.get_last_headnum()
    head = settings.get_head(headnum)
    if headnum != 0 or head is None or head.headobj is None:
        raise RuntimeError("FaceBuilder did not register exactly one head")

    camera_records = []
    FBLoader.load_model(headnum)
    for record in references:
        camera = FBLoader.add_new_camera_with_image(headnum, record["path"])
        camnum = head.get_last_camnum()
        try:
            read_exif_to_camera(headnum, camnum, record["path"])
        except RuntimeError:
            # Generated canonical images normally have no useful EXIF. Keep
            # FaceBuilder's calibrated default rather than inventing metadata.
            pass
        if not camera.auto_focal_estimation:
            auto_setup_camera_from_exif(camera)
        FBLoader.center_geo_camera_projection(headnum, camnum)
        image = _init_fb_detected_faces(FBLoader.get_builder(), headnum, camnum)
        if image is None:
            raise RuntimeError(f"face detector could not load canonical view: {record['index']}")
        detected_faces = sort_detected_faces()
        if len(detected_faces) != 1:
            raise RuntimeError(
                f"canonical view {record['index']} produced {len(detected_faces)} faces; "
                "refusing ambiguous automatic selection"
            )
        if not _add_pins_to_face(headnum, camnum, rectangle_index=0):
            raise RuntimeError(f"automatic pin solve failed: {record['index']}")
        pin_count = FBLoader.get_builder().pins_count(camera.get_keyframe())
        if pin_count < 4:
            raise RuntimeError(f"insufficient pins after solve: {record['index']}={pin_count}")
        camera_records.append({**record, "cameraIndex": camnum,
                               "keyframe": camera.get_keyframe(),
                               "detectedFaceCount": 1,
                               "pinCount": pin_count,
                               "autoPinsApproved": False})
    FBLoader.save_fb_serial_and_image_pathes(headnum)

    OUTPUT_BLEND.parent.mkdir(parents=True, exist_ok=False)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT_BLEND), check_existing=False)
    report = {
        "schemaVersion": 1,
        "iteration": "v158",
        "state": "facebuilder-autofit-generated-awaiting-pin-review",
        "tool": "KeenTools FaceBuilder 2026.3.0",
        "blender": bpy.app.version_string,
        "workspace": {"path": str(OUTPUT_BLEND), "sha256": digest_v158(OUTPUT_BLEND)},
        "headObject": head.headobj.name,
        "cameras": camera_records,
        "requiredNextActions": [
            "visually verify eye corners, lip corners, nose, jaw and ear pins",
            "correct rejected pins without changing canonical identity",
            "solve one coherent head across all four views"
        ],
        "automaticApproval": False,
        "identityCandidate": False,
        "productionReady": False,
    }
    OUTPUT_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(bootstrap_facebuilder_workspace_v158(), ensure_ascii=False))
