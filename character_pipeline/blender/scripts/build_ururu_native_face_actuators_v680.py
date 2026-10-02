#!/usr/bin/env python3
"""Build a reversible native facial-actuator proof for stylized Ururu."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import deque
from pathlib import Path
import sys

import bpy
from mathutils import Vector


EYE_CENTER_X = 0.0369
EYE_CENTER_Z = 1.2387
EYE_WIDTH = 0.051
EYE_HEIGHT = 0.026
EYELID_FRONT_Y = -0.101
IRIS_COMPONENT_RANKS = {9, 10, 18, 19}
MOUTH_COMPONENT_RANKS = {3, 6, 7, 8, 11, 12, 17}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output-blend", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(values)


def connected_components(mesh: bpy.types.Mesh) -> list[list[int]]:
    adjacency = [[] for _ in mesh.vertices]
    for edge in mesh.edges:
        left, right = edge.vertices
        adjacency[left].append(right)
        adjacency[right].append(left)
    unseen = set(range(len(mesh.vertices)))
    result = []
    while unseen:
        seed = min(unseen)
        unseen.remove(seed)
        queue = deque([seed])
        component = []
        while queue:
            current = queue.popleft()
            component.append(current)
            for neighbor in adjacency[current]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    queue.append(neighbor)
        result.append(sorted(component))
    return sorted(result, key=len, reverse=True)


def set_key_value(key_block: bpy.types.ShapeKey, frame: int, value: float) -> None:
    key_block.value = value
    key_block.keyframe_insert(data_path="value", frame=frame)


def build_head_shape_keys(head: bpy.types.Object, components: list[list[int]]) -> dict:
    basis = head.shape_key_add(name="Basis")
    basis.interpolation = "KEY_LINEAR"
    gaze_left = head.shape_key_add(name="GazeLeft")
    gaze_right = head.shape_key_add(name="GazeRight")
    jaw_open = head.shape_key_add(name="JawOpen")

    iris_indices = {
        index
        for rank, component in enumerate(components, start=1)
        if rank in IRIS_COMPONENT_RANKS
        for index in component
    }
    for index in iris_indices:
        gaze_left.data[index].co.x -= 0.0025
        gaze_right.data[index].co.x += 0.0025

    mouth_indices = {
        index
        for rank, component in enumerate(components, start=1)
        if rank in MOUTH_COMPONENT_RANKS
        for index in component
    }
    moved_mouth = 0
    for index in mouth_indices:
        point = jaw_open.data[index].co
        if point.z < 1.192:
            vertical_weight = min(1.0, max(0.0, (1.192 - point.z) / 0.018))
            point.z -= 0.0020 * vertical_weight
            point.y += 0.0008 * vertical_weight
            moved_mouth += 1

    for key in (gaze_left, gaze_right, jaw_open):
        for frame in (1, 10, 20, 30, 40):
            set_key_value(key, frame, 0.0)
    set_key_value(gaze_left, 20, 1.0)
    set_key_value(gaze_right, 30, 1.0)
    set_key_value(jaw_open, 40, 1.0)
    return {
        "irisVertexCount": len(iris_indices),
        "mouthCandidateVertexCount": len(mouth_indices),
        "mouthMovedVertexCount": moved_mouth,
        "gazeMaxDisplacementMeters": 0.0025,
        "jawMaxDisplacementMeters": math.sqrt(0.0020**2 + 0.0008**2),
    }


def create_skin_material() -> bpy.types.Material:
    material = bpy.data.materials.new("Ururu_EyelidSkin_v680")
    material.diffuse_color = (0.42, 0.36, 0.35, 1.0)
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = (0.42, 0.36, 0.35, 1.0)
    principled.inputs["Roughness"].default_value = 0.58
    return material


def create_eyelid(side: str, center_x: float, material: bpy.types.Material) -> bpy.types.Object:
    segments = 24
    vertices = []
    faces = []
    for index in range(segments + 1):
        x_unit = -1.0 + 2.0 * index / segments
        x = center_x + x_unit * EYE_WIDTH * 0.5
        upper_z = EYE_CENTER_Z + math.sqrt(max(0.0, 1.0 - x_unit * x_unit)) * EYE_HEIGHT * 0.52
        vertices.extend(((x, EYELID_FRONT_Y, upper_z + 0.0006), (x, EYELID_FRONT_Y, upper_z - 0.0006)))
        if index:
            base = index * 2
            faces.append((base - 2, base, base + 1, base - 1))

    mesh = bpy.data.meshes.new(f"Ururu_Eyelid_{side}_Mesh_v680")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(material)
    mesh.update()
    eyelid = bpy.data.objects.new(f"Ururu_Eyelid_{side}_v680", mesh)
    bpy.context.scene.collection.objects.link(eyelid)
    eyelid.shape_key_add(name="Basis")
    blink = eyelid.shape_key_add(name=f"EyeBlink_{side}")
    for index in range(segments + 1):
        x_unit = -1.0 + 2.0 * index / segments
        lower_z = EYE_CENTER_Z - math.sqrt(max(0.0, 1.0 - x_unit * x_unit)) * EYE_HEIGHT * 0.52
        blink.data[index * 2 + 1].co.z = lower_z
    for frame in (1, 10, 20, 30, 40):
        set_key_value(blink, frame, 0.0)
    set_key_value(blink, 10, 1.0)
    return eyelid


def setup_render(output_dir: Path, head: bpy.types.Object) -> list[dict]:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.resolution_x = 1024
    scene.render.resolution_y = 1024
    scene.render.resolution_percentage = 100
    scene.view_settings.look = "AgX - Medium High Contrast"

    world = scene.world or bpy.data.worlds.new("UruruNativeFaceWorld_v680")
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.035, 0.04, 0.055, 1.0)
    background.inputs["Strength"].default_value = 0.5

    center = Vector((0.0, -0.02, 1.245))
    for name, location, energy, size in (
        ("Key", Vector((-0.65, -0.9, 1.8)), 850.0, 0.75),
        ("Fill", Vector((0.65, -0.65, 1.5)), 500.0, 0.65),
        ("Rim", Vector((0.0, 0.55, 1.65)), 650.0, 0.55),
    ):
        light_data = bpy.data.lights.new(f"UruruNativeFace{name}_v680", "AREA")
        light_data.energy = energy
        light_data.shape = "DISK"
        light_data.size = size
        light = bpy.data.objects.new(f"UruruNativeFace{name}_v680", light_data)
        scene.collection.objects.link(light)
        light.location = location
        light.rotation_euler = (center - location).to_track_quat("-Z", "Y").to_euler()

    camera_data = bpy.data.cameras.new("UruruNativeFaceCamera_v680")
    camera = bpy.data.objects.new("UruruNativeFaceCamera_v680", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.location = Vector((0.0, -0.62, 1.245))
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 0.36

    frames = (("neutral", 1), ("blink", 10), ("gaze-left", 20), ("gaze-right", 30), ("jaw-open", 40))
    renders = []
    for name, frame in frames:
        scene.frame_set(frame)
        scene.render.filepath = str(output_dir / f"{name}.png")
        bpy.ops.render.render(write_still=True)
        path = output_dir / f"{name}.png"
        renders.append({"pose": name, "frame": frame, "file": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    return renders


def main() -> None:
    args = parse_args()
    source = args.source.resolve()
    output_blend = args.output_blend.resolve()
    output_dir = args.output_dir.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if output_blend.exists() or output_dir.exists():
        raise FileExistsError("refusing to overwrite immutable v680 output")
    output_blend.parent.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True)
    if Path(bpy.data.filepath).resolve() != source:
        bpy.ops.wm.open_mainfile(filepath=str(source))

    head = bpy.data.objects.get("head.")
    if head is None or head.type != "MESH":
        raise RuntimeError("Ururu head mesh was not found")
    armature = bpy.data.objects.get("ARM")
    if armature:
        armature.data.pose_position = "REST"
    components = connected_components(head.data)
    head_metrics = build_head_shape_keys(head, components)
    eyelid_material = create_skin_material()
    eyelids = [
        create_eyelid("L", -EYE_CENTER_X, eyelid_material),
        create_eyelid("R", EYE_CENTER_X, eyelid_material),
    ]
    for eyelid in eyelids:
        eyelid.parent = head
        eyelid.matrix_parent_inverse = head.matrix_world.inverted()

    bpy.ops.wm.save_as_mainfile(filepath=str(output_blend))
    renders = setup_render(output_dir, head)
    report = {
        "schemaVersion": 1,
        "iteration": "v680",
        "status": "authored-draft-native-face-actuator-proof",
        "source": str(source),
        "sourceSha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "outputBlend": str(output_blend),
        "outputBlendSha256": hashlib.sha256(output_blend.read_bytes()).hexdigest(),
        "headShapeKeys": [key.name for key in head.data.shape_keys.key_blocks],
        "eyelidObjects": [eyelid.name for eyelid in eyelids],
        "metrics": head_metrics,
        "poses": renders,
        "hypothesis": "Separate eyelid actuators and component-scoped iris/mouth morphs can add basic life without altering Ururu's neutral identity surface.",
        "expectedResult": "Readable blink and gaze with no neutral-frame regression; jaw proof remains conservative.",
        "decision": "draft pending direct visual comparison; no UE import authorized",
        "automaticApproval": False,
        "humanApproved": False,
        "productionReady": False,
    }
    (output_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"iteration": "v680", "shapeKeys": report["headShapeKeys"], "poses": len(renders)}))


if __name__ == "__main__":
    main()
