#!/usr/bin/env python3
"""Render and measure Hayley's immutable source rest/action poses."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args(values)


def world_bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    return (
        Vector(tuple(min(point[i] for point in points) for i in range(3))),
        Vector(tuple(max(point[i] for point in points) for i in range(3))),
    )


def render_view(
    output: Path,
    camera: bpy.types.Object,
    center: Vector,
    span: float,
    direction: Vector,
) -> None:
    camera.location = center + direction.normalized() * span * 2.4
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = span * 1.16
    bpy.context.scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)


def inspect_hayley_source_v443(source: Path, output_dir: Path) -> dict[str, object]:
    if not source.is_file():
        raise FileNotFoundError(source)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"refusing to overwrite immutable diagnostic: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(source))
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    if len(armatures) != 1:
        raise RuntimeError(f"expected one armature, found {len(armatures)}")
    armature = armatures[0]
    meshes = [
        obj for obj in bpy.context.scene.objects
        if obj.type == "MESH" and not obj.hide_render and len(obj.data.polygons) > 100
    ]
    if not meshes:
        raise RuntimeError("source contains no visible mesh")

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "WORLD"
    scene.render.resolution_x = 768
    scene.render.resolution_y = 1024
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False

    camera_data = bpy.data.cameras.new("HayleySourceDiagnosticCamera_v443")
    camera = bpy.data.objects.new("HayleySourceDiagnosticCamera_v443", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera

    armature.data.pose_position = "REST"
    scene.frame_set(1)
    bpy.context.view_layer.update()
    minimum, maximum = world_bounds(meshes)
    center = (minimum + maximum) * 0.5
    span = max(maximum.x - minimum.x, maximum.z - minimum.z)
    renders = []
    for pose_name, pose_position, frame in (
        ("rest", "REST", 1),
        ("action-start", "POSE", 1),
        ("action-middle", "POSE", 116),
        ("action-end", "POSE", 231),
    ):
        armature.data.pose_position = pose_position
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        for view_name, direction in (("front-y", Vector((0, -1, 0))), ("side-x", Vector((1, 0, 0)))):
            path = output_dir / f"{pose_name}-{view_name}.png"
            render_view(path, camera, center, span, direction)
            renders.append({"pose": pose_name, "frame": frame, "view": view_name, "file": str(path.resolve())})

    armature.data.pose_position = "REST"
    scene.frame_set(1)
    bpy.context.view_layer.update()
    bone_names = {bone.name for bone in armature.data.bones}
    arm_terms = ("shoulder", "clavicle", "upperarm", "forearm", "lowerarm", "hand")
    arm_bones = sorted(name for name in bone_names if any(term in name.lower() for term in arm_terms))
    mesh_inventory = []
    for mesh in meshes:
        mesh_minimum, mesh_maximum = world_bounds([mesh])
        modifiers = [mod.object.name for mod in mesh.modifiers if mod.type == "ARMATURE" and mod.object]
        weighted_arm_groups = sorted(group.name for group in mesh.vertex_groups if group.name in arm_bones)
        mesh_inventory.append({
            "name": mesh.name,
            "vertices": len(mesh.data.vertices),
            "polygons": len(mesh.data.polygons),
            "materials": [slot.material.name if slot.material else None for slot in mesh.material_slots],
            "armatureModifiers": modifiers,
            "vertexGroupCount": len(mesh.vertex_groups),
            "weightedArmGroups": weighted_arm_groups,
            "bounds": {"minimum": list(mesh_minimum), "maximum": list(mesh_maximum)},
        })

    report = {
        "schemaVersion": 1,
        "iteration": "v443",
        "status": "diagnostic-draft",
        "hypothesis": "Hayley's apparently missing arms originate in the source reference/action pose or mesh binding, not solely in UE retargeting.",
        "source": {
            "file": str(source.resolve()),
            "bytes": source.stat().st_size,
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        },
        "armature": {
            "name": armature.name,
            "boneCount": len(armature.data.bones),
            "armBones": arm_bones,
            "action": armature.animation_data.action.name if armature.animation_data and armature.animation_data.action else None,
        },
        "bounds": {"minimum": list(minimum), "maximum": list(maximum)},
        "meshes": mesh_inventory,
        "renders": renders,
        "humanApproved": False,
        "releaseEligible": False,
    }
    (output_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    args = parse_args()
    report = inspect_hayley_source_v443(args.input, args.output_dir)
    print(json.dumps({
        "iteration": report["iteration"],
        "meshCount": len(report["meshes"]),
        "armBoneCount": len(report["armature"]["armBones"]),
        "renderCount": len(report["renders"]),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
