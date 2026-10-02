#!/usr/bin/env python3
"""Apply a sealed G1 scene plan inside Blender and save a new .blend file."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

try:
    import bpy
    from mathutils import Vector
except ImportError as error:  # pragma: no cover - executed only by Blender
    raise SystemExit("Run this script with Blender's Python runtime") from error


def parse_args() -> argparse.Namespace:
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--handoff-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(args)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def link_only(obj, collection) -> None:
    for current in tuple(obj.users_collection):
        current.objects.unlink(obj)
    collection.objects.link(obj)


def point_camera(camera, target) -> None:
    direction = Vector(target) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def main() -> None:
    args = parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    handoff = args.handoff_dir.resolve()
    manifest = handoff / plan["source"]["packageManifest"]
    work_order = handoff / plan["source"]["workOrder"]
    if sha256(manifest) != plan["source"]["packageManifestSha256"]:
        raise SystemExit("G1 package manifest changed after scene planning")
    if sha256(work_order) != plan["source"]["workOrderSha256"]:
        raise SystemExit("G1 work order changed after scene planning")
    if args.output.exists():
        raise SystemExit(f"Refusing to overwrite existing Blender file: {args.output}")

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in tuple(bpy.data.collections):
        bpy.data.collections.remove(collection)

    scene = bpy.context.scene
    scene.unit_settings.system = plan["scene"]["unitSystem"]
    scene.unit_settings.scale_length = plan["scene"]["unitScale"]
    scene["gahyeon_character_id"] = plan["characterId"]
    scene["gahyeon_gate"] = plan["gate"]
    scene["gahyeon_neutral_pose"] = plan["scene"]["neutralPose"]
    scene["gahyeon_scene_plan_sha256"] = sha256(args.plan)

    collections = {}
    for name in plan["scene"]["collections"]:
        collection = bpy.data.collections.new(name)
        scene.collection.children.link(collection)
        collections[name] = collection

    root = bpy.data.objects.new(plan["scene"]["rootObject"], None)
    root.empty_display_type = "PLAIN_AXES"
    root["authoring_units"] = "centimeters"
    collections["G1_MODEL_BODY"].objects.link(root)

    guides = plan["authoringGuides"]
    scene["gahyeon_guide_authority"] = guides["authority"]
    scene["gahyeon_guide_basis"] = guides["basis"]
    symmetry = bpy.data.objects.new("GUIDE_SYMMETRY_X0", None)
    symmetry.empty_display_type = "PLAIN_AXES"
    symmetry.empty_display_size = 200.0
    symmetry["plane"] = guides["symmetryPlane"]
    symmetry["identity_authority"] = False
    collections["G1_GUIDES_NON_AUTHORITATIVE"].objects.link(symmetry)
    for name, position in guides["landmarksCm"].items():
        guide = bpy.data.objects.new(f"GUIDE_{name.upper()}", None)
        guide.empty_display_type = "SPHERE"
        guide.empty_display_size = 2.0
        guide.location = position
        guide["identity_authority"] = False
        guide["must_adjust_to_canonical_references"] = True
        collections["G1_GUIDES_NON_AUTHORITATIVE"].objects.link(guide)

    for order, item in enumerate(plan["referenceImages"]):
        image_path = (handoff / item["path"]).resolve()
        if handoff not in image_path.parents or sha256(image_path) != item["sha256"]:
            raise SystemExit(f"Reference failed integrity check: {item['index']}")
        image = bpy.data.images.load(str(image_path), check_existing=True)
        obj = bpy.data.objects.new(f"REF_G1_{item['index']:03d}", None)
        obj.empty_display_type = "IMAGE"
        obj.data = image
        obj.empty_display_size = 40.0
        obj.location = ((order % 5) * 45.0, 100.0 + (order // 5) * 45.0, 90.0)
        obj.rotation_euler = (math.radians(90.0), 0.0, 0.0)
        obj["identity_authority"] = item["classification"]
        obj["source_index"] = item["index"]
        obj["source_sha256"] = item["sha256"]
        collection_name = (
            "G1_REFERENCES_CANONICAL"
            if item["classification"] == "canonical"
            else "G1_REFERENCES_SUPPORTING"
        )
        collections[collection_name].objects.link(obj)

    for item in plan["evidenceCameras"]:
        camera_data = bpy.data.cameras.new(item["name"])
        camera_data.type = "ORTHO"
        camera_data.ortho_scale = item["orthoScaleCm"]
        camera = bpy.data.objects.new(item["name"], camera_data)
        camera.location = item["locationCm"]
        point_camera(camera, item["targetCm"])
        camera["evidence_view"] = item["view"]
        camera["design_authority"] = item["designAuthority"]
        camera["source_anchors"] = json.dumps(item["sourceAnchors"])
        collections["G1_EVIDENCE_CAMERAS"].objects.link(camera)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()), check_existing=False)
    print(json.dumps({"saved": str(args.output.resolve()),
                      "references": len(plan["referenceImages"]),
                      "cameras": len(plan["evidenceCameras"])}))


if __name__ == "__main__":
    main()
