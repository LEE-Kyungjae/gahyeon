"""Export the immutable v177 FaceBuilder control head for neutral QA."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy


TARGET_HEAD_HEIGHT_CM = 29.535091
EXPECTED_FOCAL_MM = 65.0


def digest_export_v177(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export_common_focal_head_v177() -> dict:
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(values)
    output = args.output_dir.resolve()
    if output.exists():
        raise RuntimeError(f"refusing to overwrite immutable output: {output}")
    source = Path(bpy.data.filepath).resolve()
    if not source.is_file():
        raise RuntimeError("saved v177 FaceBuilder workspace required")

    from keentools.addon_config import fb_settings
    from keentools.facebuilder.fbloader import FBLoader

    settings = fb_settings()
    if len(settings.heads) != 1:
        raise RuntimeError(f"expected one FaceBuilder head, found {len(settings.heads)}")
    head = settings.get_head(0)
    if head.headobj is None or len(head.cameras) != 5:
        raise RuntimeError("v177 head or five-camera contract differs")
    if not FBLoader.load_model(0):
        raise RuntimeError("could not load serialized FaceBuilder model")
    builder = FBLoader.get_builder()
    camera_records = []
    for index, camera in enumerate(head.cameras):
        focal = float(camera.focal)
        if camera.auto_focal_estimation or abs(focal - EXPECTED_FOCAL_MM) > 0.001:
            raise RuntimeError(f"camera {index} violates fixed focal contract: {focal}")
        pin_count = builder.pins_count(camera.get_keyframe())
        if pin_count < 4:
            raise RuntimeError(f"camera {index} has insufficient pins: {pin_count}")
        camera_records.append({
            "cameraIndex": index,
            "pinCount": pin_count,
            "focalMm": focal,
            "imagePath": camera.get_abspath(),
        })

    source_head = head.headobj
    if source_head.type != "MESH" or len(source_head.data.vertices) < 1000:
        raise RuntimeError("FaceBuilder source head lacks expected mesh density")
    normalized = source_head.copy()
    normalized.data = source_head.data.copy()
    normalized.name = "Gahyeon_FaceBuilder_CommonFocal_v177"
    bpy.context.scene.collection.objects.link(normalized)
    source_height_m = float(normalized.dimensions.z)
    if source_height_m <= 0:
        raise RuntimeError("FaceBuilder source head has zero height")
    scale = (TARGET_HEAD_HEIGHT_CM / 100.0) / source_height_m
    normalized.scale = tuple(value * scale for value in normalized.scale)
    bpy.ops.object.select_all(action="DESELECT")
    normalized.select_set(True)
    bpy.context.view_layer.objects.active = normalized
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    measured_height_cm = float(normalized.dimensions.z) * 100.0
    if abs(measured_height_cm - TARGET_HEAD_HEIGHT_CM) > 0.01:
        raise RuntimeError(f"head normalization drifted: {measured_height_cm}")

    output.mkdir(parents=True, exist_ok=False)
    source_head.hide_set(True)
    obj_path = output / "gahyeon-facebuilder-common-focal-v177.obj"
    bpy.ops.wm.obj_export(
        filepath=str(obj_path),
        export_selected_objects=True,
        export_materials=True,
        export_uv=True,
        export_normals=True,
        export_triangulated_mesh=False,
        path_mode="COPY",
        forward_axis="NEGATIVE_Z",
        up_axis="Y",
    )
    payload = {
        "schemaVersion": 1,
        "iteration": "v177",
        "status": "normalized-shape-estimate-awaiting-identity-render",
        "sourceWorkspace": {"path": str(source), "sha256": digest_export_v177(source)},
        "commonFocalMm": EXPECTED_FOCAL_MM,
        "cameras": camera_records,
        "normalization": {
            "sourceHeightBlenderMeters": source_height_m,
            "uniformScaleFactor": scale,
            "targetHeadHeightCm": TARGET_HEAD_HEIGHT_CM,
            "measuredHeadHeightCm": measured_height_cm,
            "identityShapeChanged": False,
        },
        "topology": {
            "vertices": len(normalized.data.vertices),
            "polygons": len(normalized.data.polygons),
            "uvLayers": [layer.name for layer in normalized.data.uv_layers],
        },
        "model": {
            "path": str(obj_path),
            "bytes": obj_path.stat().st_size,
            "sha256": digest_export_v177(obj_path),
        },
        "automaticApproval": False,
        "metaHumanConformAllowed": False,
    }
    (output / "manifest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "iteration": "v177",
        "model": str(obj_path),
        "vertices": payload["topology"]["vertices"],
        "heightCm": measured_height_cm,
    }))
    return payload


if __name__ == "__main__":
    try:
        export_common_focal_head_v177()
    except RuntimeError as error:
        raise SystemExit(f"ERROR: {error}")
