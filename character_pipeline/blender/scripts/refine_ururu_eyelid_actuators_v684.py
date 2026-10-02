#!/usr/bin/env python3
"""Refine Ururu's separate eyelid proof with curved skin and a lash seam."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector


EYE_CENTER_X = 0.0369
EYE_CENTER_Z = 1.2387
EYE_WIDTH = 0.051
EYE_HEIGHT = 0.026
FRAMES = (("neutral", 1), ("blink", 10), ("gaze-screen-left", 20), ("gaze-screen-right", 30))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output-blend", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(values)


def key_value(key: bpy.types.ShapeKey, frame: int, value: float) -> None:
    key.value = value
    key.keyframe_insert(data_path="value", frame=frame)


def material(name: str, color: tuple[float, float, float, float], roughness: float) -> bpy.types.Material:
    result = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    result.diffuse_color = color
    result.use_nodes = True
    principled = result.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = color
    principled.inputs["Roughness"].default_value = roughness
    return result


def create_lid(side: str, center_x: float, skin: bpy.types.Material, head: bpy.types.Object) -> bpy.types.Object:
    segments = 24
    rows = 7
    vertices = []
    faces = []
    for x_index in range(segments + 1):
        x_unit = -1.0 + 2.0 * x_index / segments
        height = math.sqrt(max(0.0, 1.0 - x_unit * x_unit)) * EYE_HEIGHT * 0.52
        upper = EYE_CENTER_Z + height
        for row in range(rows):
            vertices.append((center_x + x_unit * EYE_WIDTH * 0.5, -0.101, upper - row * 0.00012))
        if x_index:
            base = x_index * rows
            for row in range(rows - 1):
                faces.append((base - rows + row, base + row, base + row + 1, base - rows + row + 1))
    mesh = bpy.data.meshes.new(f"UruruCurvedEyelid_{side}_Mesh_v684")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(skin)
    mesh.update()
    obj = bpy.data.objects.new(f"UruruCurvedEyelid_{side}_v684", mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = head
    obj.matrix_parent_inverse = head.matrix_world.inverted()
    obj.shape_key_add(name="Basis")
    blink = obj.shape_key_add(name=f"EyeBlink_{side}")
    for x_index in range(segments + 1):
        x_unit = -1.0 + 2.0 * x_index / segments
        radial = math.sqrt(max(0.0, 1.0 - x_unit * x_unit))
        upper = EYE_CENTER_Z + radial * EYE_HEIGHT * 0.52
        lower = EYE_CENTER_Z - radial * EYE_HEIGHT * 0.52
        for row in range(rows):
            fraction = row / (rows - 1)
            index = x_index * rows + row
            blink.data[index].co.z = upper * (1.0 - fraction) + lower * fraction
            blink.data[index].co.y = -0.101 - math.sin(math.pi * fraction) * radial * 0.003
    for _, frame in FRAMES:
        key_value(blink, frame, 0.0)
    key_value(blink, 10, 1.0)
    return obj


def create_lash(side: str, center_x: float, lash_material: bpy.types.Material, head: bpy.types.Object) -> bpy.types.Object:
    segments = 24
    thickness = 0.00065
    vertices = []
    faces = []
    for x_index in range(segments + 1):
        x_unit = -1.0 + 2.0 * x_index / segments
        radial = math.sqrt(max(0.0, 1.0 - x_unit * x_unit))
        upper = EYE_CENTER_Z + radial * EYE_HEIGHT * 0.53
        vertices.extend(((center_x + x_unit * EYE_WIDTH * 0.5, -0.1045, upper + thickness), (center_x + x_unit * EYE_WIDTH * 0.5, -0.1045, upper - thickness)))
        if x_index:
            base = x_index * 2
            faces.append((base - 2, base, base + 1, base - 1))
    mesh = bpy.data.meshes.new(f"UruruBlinkLash_{side}_Mesh_v684")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(lash_material)
    mesh.update()
    obj = bpy.data.objects.new(f"UruruBlinkLash_{side}_v684", mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = head
    obj.matrix_parent_inverse = head.matrix_world.inverted()
    obj.shape_key_add(name="Basis")
    blink = obj.shape_key_add(name=f"EyeBlink_{side}")
    for x_index in range(segments + 1):
        x_unit = -1.0 + 2.0 * x_index / segments
        closed = EYE_CENTER_Z - 0.0018 * (1.0 - x_unit * x_unit)
        blink.data[x_index * 2].co.z = closed + thickness
        blink.data[x_index * 2 + 1].co.z = closed - thickness
    for _, frame in FRAMES:
        key_value(blink, frame, 0.0)
    key_value(blink, 10, 1.0)
    return obj


def configure_render(output_dir: Path) -> tuple[bpy.types.Object, list[dict]]:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.resolution_x = 1024
    scene.render.resolution_y = 1024
    scene.render.resolution_percentage = 100
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = -1.25
    world = scene.world or bpy.data.worlds.new("UruruRefinedEyelidWorld_v684")
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.045, 0.05, 0.065, 1.0)
    background.inputs["Strength"].default_value = 0.12
    center = Vector((0.0, -0.02, 1.245))
    for name, location, energy, size in (
        ("Key", Vector((-0.55, -0.75, 1.65)), 35.0, 0.7),
        ("Fill", Vector((0.55, -0.6, 1.45)), 18.0, 0.65),
    ):
        light_data = bpy.data.lights.new(f"UruruRefinedEyelid{name}_v684", "AREA")
        light_data.energy = energy
        light_data.shape = "DISK"
        light_data.size = size
        light = bpy.data.objects.new(f"UruruRefinedEyelid{name}_v684", light_data)
        scene.collection.objects.link(light)
        light.location = location
        light.rotation_euler = (center - light.location).to_track_quat("-Z", "Y").to_euler()
    camera_data = bpy.data.cameras.new("UruruRefinedEyelidCamera_v684")
    camera = bpy.data.objects.new("UruruRefinedEyelidCamera_v684", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.location = Vector((0.0, -0.62, 1.245))
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 0.36
    renders = []
    for pose, frame in FRAMES:
        scene.frame_set(frame)
        path = output_dir / f"{pose}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        renders.append({"pose": pose, "frame": frame, "file": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    return camera, renders


def main() -> None:
    args = parse_args()
    source = args.source.resolve()
    output_blend = args.output_blend.resolve()
    output_dir = args.output_dir.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if output_blend.exists() or output_dir.exists():
        raise FileExistsError("refusing to overwrite immutable v684 output")
    output_blend.parent.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True)
    if Path(bpy.data.filepath).resolve() != source:
        bpy.ops.wm.open_mainfile(filepath=str(source))
    head = bpy.data.objects.get("head.")
    if head is None or head.type != "MESH":
        raise RuntimeError("Ururu head mesh was not found")
    jaw = head.data.shape_keys.key_blocks.get("JawOpen") if head.data.shape_keys else None
    if jaw is not None:
        head.shape_key_remove(jaw)
    for name in ("Ururu_Eyelid_L_v680", "Ururu_Eyelid_R_v680"):
        old = bpy.data.objects.get(name)
        if old is not None:
            bpy.data.objects.remove(old, do_unlink=True)
    skin = material("Ururu_EyelidSkin_v684", (0.62, 0.50, 0.46, 1.0), 0.62)
    lash = material("Ururu_BlinkLash_v684", (0.025, 0.018, 0.025, 1.0), 0.42)
    actuators = []
    for side, center_x in (("L", EYE_CENTER_X), ("R", -EYE_CENTER_X)):
        actuators.extend((create_lid(side, center_x, skin, head), create_lash(side, center_x, lash, head)))
    camera, renders = configure_render(output_dir)
    bpy.ops.wm.save_as_mainfile(filepath=str(output_blend))
    report = {
        "schemaVersion": 1,
        "iteration": "v684",
        "status": "authored-draft-refined-eyelid-actuators",
        "source": str(source),
        "sourceSha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "outputBlend": str(output_blend),
        "outputBlendSha256": hashlib.sha256(output_blend.read_bytes()).hexdigest(),
        "retainedHeadShapeKeys": [key.name for key in head.data.shape_keys.key_blocks],
        "actuatorObjects": [obj.name for obj in actuators],
        "skinColor": list(skin.diffuse_color),
        "camera": camera.name,
        "renders": renders,
        "hypothesis": "A curved two-surface eyelid with a center lash seam will read as a stylized closed eye while preserving the source eyeballs and neutral identity.",
        "decision": "draft pending direct visual review; no UE import authorized",
        "automaticApproval": False,
        "humanApproved": False,
        "productionReady": False,
    }
    (output_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"iteration": "v684", "actuators": len(actuators), "renderCount": len(renders)}))


if __name__ == "__main__":
    main()
