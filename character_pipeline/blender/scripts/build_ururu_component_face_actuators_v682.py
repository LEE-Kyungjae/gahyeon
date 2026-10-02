#!/usr/bin/env python3
"""Build Ururu blink and gaze from original disconnected eye components only."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import deque
from pathlib import Path
import sys

import bpy
from mathutils import Vector


EYE_CENTER_Z = 1.2387
IRIS_COMPONENT_RANKS = {9, 10, 18, 19}
FRAMES = (("neutral", 1), ("blink", 10), ("gaze-screen-left", 20), ("gaze-screen-right", 30))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output-blend", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(values)


def components(mesh: bpy.types.Mesh) -> list[list[int]]:
    adjacency = [[] for _ in mesh.vertices]
    for edge in mesh.edges:
        left, right = edge.vertices
        adjacency[left].append(right)
        adjacency[right].append(left)
    unseen = set(range(len(mesh.vertices)))
    found = []
    while unseen:
        seed = min(unseen)
        unseen.remove(seed)
        queue = deque([seed])
        group = []
        while queue:
            current = queue.popleft()
            group.append(current)
            for neighbor in adjacency[current]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    queue.append(neighbor)
        found.append(sorted(group))
    return sorted(found, key=len, reverse=True)


def key_value(key: bpy.types.ShapeKey, frame: int, value: float) -> None:
    key.value = value
    key.keyframe_insert(data_path="value", frame=frame)


def component_center(mesh: bpy.types.Mesh, indices: list[int]) -> Vector:
    points = [mesh.vertices[index].co for index in indices]
    minimum = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
    maximum = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
    return (minimum + maximum) * 0.5


def build_controls(head: bpy.types.Object, groups: list[list[int]]) -> dict:
    basis = head.shape_key_add(name="Basis")
    basis.interpolation = "KEY_LINEAR"
    blink_l = head.shape_key_add(name="EyeBlink_L")
    blink_r = head.shape_key_add(name="EyeBlink_R")
    gaze_left = head.shape_key_add(name="GazeScreenLeft")
    gaze_right = head.shape_key_add(name="GazeScreenRight")

    selected_eye_ranks = []
    selected_eye_vertices = {"L": set(), "R": set()}
    for rank, group in enumerate(groups, start=1):
        center = component_center(head.data, group)
        is_eye_detail = (
            0.014 < abs(center.x) < 0.061
            and 1.215 < center.z < 1.272
            and center.y < -0.060
        )
        if not is_eye_detail:
            continue
        side = "L" if center.x > 0 else "R"
        selected_eye_ranks.append(rank)
        selected_eye_vertices[side].update(group)
        target = blink_l if side == "L" else blink_r
        for index in group:
            point = target.data[index].co
            point.z = EYE_CENTER_Z + (point.z - EYE_CENTER_Z) * 0.06

    iris_indices = set()
    for rank, group in enumerate(groups, start=1):
        if rank in IRIS_COMPONENT_RANKS:
            iris_indices.update(group)
    for index in iris_indices:
        gaze_left.data[index].co.x -= 0.0025
        gaze_right.data[index].co.x += 0.0025

    keys = (blink_l, blink_r, gaze_left, gaze_right)
    for key in keys:
        for _, frame in FRAMES:
            key_value(key, frame, 0.0)
    key_value(blink_l, 10, 1.0)
    key_value(blink_r, 10, 1.0)
    key_value(gaze_left, 20, 1.0)
    key_value(gaze_right, 30, 1.0)
    return {
        "selectedEyeComponentRanks": selected_eye_ranks,
        "selectedEyeVertexCounts": {key: len(value) for key, value in selected_eye_vertices.items()},
        "irisVertexCount": len(iris_indices),
        "blinkVerticalScale": 0.06,
        "gazeDisplacementMeters": 0.0025,
    }


def configure_camera(scene: bpy.types.Scene) -> bpy.types.Object:
    camera_data = bpy.data.cameras.new("UruruComponentFaceCamera_v682")
    camera = bpy.data.objects.new("UruruComponentFaceCamera_v682", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    center = Vector((0.0, -0.02, 1.245))
    camera.location = Vector((0.0, -0.62, 1.245))
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 0.36
    return camera


def render_qa(output_dir: Path) -> tuple[bpy.types.Object, list[dict]]:
    scene = bpy.context.scene
    camera = configure_camera(scene)
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.studio_light = "paint.sl"
    scene.display.shading.color_type = "TEXTURE"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "WORLD"
    scene.display.shading.show_specular_highlight = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.resolution_x = 1024
    scene.render.resolution_y = 1024
    scene.render.resolution_percentage = 100
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
        raise FileExistsError("refusing to overwrite immutable v682 output")
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

    metrics = build_controls(head, components(head.data))
    camera, renders = render_qa(output_dir)
    bpy.ops.wm.save_as_mainfile(filepath=str(output_blend))
    report = {
        "schemaVersion": 1,
        "iteration": "v682",
        "status": "authored-draft-original-component-face-actuators",
        "source": str(source),
        "sourceSha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "outputBlend": str(output_blend),
        "outputBlendSha256": hashlib.sha256(output_blend.read_bytes()).hexdigest(),
        "shapeKeys": [key.name for key in head.data.shape_keys.key_blocks],
        "metrics": metrics,
        "camera": camera.name,
        "renders": renders,
        "hypothesis": "Collapsing only original disconnected eye-detail components can produce a stylized blink without introducing foreign eyelid geometry.",
        "expectedResult": "A closed-eye line, preserved surrounding face, and retained component-scoped gaze.",
        "decision": "draft pending direct visual review; no UE import authorized",
        "automaticApproval": False,
        "humanApproved": False,
        "productionReady": False,
    }
    (output_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"iteration": "v682", "shapeKeys": report["shapeKeys"], "renderCount": len(renders)}))


if __name__ == "__main__":
    main()
