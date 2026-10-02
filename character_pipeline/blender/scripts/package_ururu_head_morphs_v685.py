#!/usr/bin/env python3
"""Merge Ururu facial actuators into one skinned head and export a UE FBX proof."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy


ACTUATORS = (
    "UruruCurvedEyelid_L_v684",
    "UruruBlinkLash_L_v684",
    "UruruCurvedEyelid_R_v684",
    "UruruBlinkLash_R_v684",
)
SHAPE_KEYS = ("GazeLeft", "GazeRight", "EyeBlink_L", "EyeBlink_R")
FRAMES = (("neutral", 1), ("blink", 10), ("gaze-screen-left", 20), ("gaze-screen-right", 30))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output-blend", required=True, type=Path)
    parser.add_argument("--output-fbx", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(values)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_shape_keys(obj: bpy.types.Object) -> None:
    if obj.data.shape_keys is None:
        obj.shape_key_add(name="Basis")
    existing = {key.name for key in obj.data.shape_keys.key_blocks}
    for name in SHAPE_KEYS:
        if name not in existing:
            obj.shape_key_add(name=name)
    for key in obj.data.shape_keys.key_blocks:
        key.value = 0.0


def prepare_actuator(obj: bpy.types.Object, armature: bpy.types.Object) -> None:
    matrix_world = obj.matrix_world.copy()
    obj.parent = None
    obj.matrix_world = matrix_world
    group = obj.vertex_groups.get("ValveBiped.Bip01_Head1") or obj.vertex_groups.new(name="ValveBiped.Bip01_Head1")
    group.add(list(range(len(obj.data.vertices))), 1.0, "REPLACE")
    modifier = obj.modifiers.get("UruruFaceArmature_v685") or obj.modifiers.new("UruruFaceArmature_v685", "ARMATURE")
    modifier.object = armature
    ensure_shape_keys(obj)


def join_head(head: bpy.types.Object, actuators: list[bpy.types.Object]) -> dict:
    before_vertices = len(head.data.vertices)
    before_polygons = len(head.data.polygons)
    ensure_shape_keys(head)
    bpy.ops.object.select_all(action="DESELECT")
    head.select_set(True)
    for obj in actuators:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = head
    bpy.ops.object.join()
    head.name = "Ururu_Head_Facial_v685"
    head.data.name = "Ururu_Head_Facial_Mesh_v685"
    return {
        "vertexCountBefore": before_vertices,
        "vertexCountAfter": len(head.data.vertices),
        "addedVertexCount": len(head.data.vertices) - before_vertices,
        "polygonCountBefore": before_polygons,
        "polygonCountAfter": len(head.data.polygons),
        "shapeKeys": [key.name for key in head.data.shape_keys.key_blocks],
        "materialSlots": [material.name if material else None for material in head.data.materials],
    }


def render_qa(output_dir: Path) -> list[dict]:
    scene = bpy.context.scene
    camera = bpy.data.objects.get("UruruRefinedEyelidCamera_v684")
    if camera is None or camera.type != "CAMERA":
        raise RuntimeError("v684 sealed camera is missing")
    scene.camera = camera
    renders = []
    for pose, frame in FRAMES:
        scene.frame_set(frame)
        path = output_dir / f"{pose}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        renders.append({"pose": pose, "frame": frame, "file": str(path), "sha256": sha256(path)})
    return renders


def export_fbx(path: Path, armature: bpy.types.Object) -> list[str]:
    bpy.ops.object.select_all(action="DESELECT")
    exported = []
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH" and not obj.name.startswith(("UruruNativeFace", "UruruRefinedEyelid")):
            obj.select_set(True)
            exported.append(obj.name)
    armature.select_set(True)
    exported.append(armature.name)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.export_scene.fbx(
        filepath=str(path),
        use_selection=True,
        object_types={"ARMATURE", "MESH"},
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_UNITS",
        use_mesh_modifiers=False,
        mesh_smooth_type="FACE",
        add_leaf_bones=False,
        use_armature_deform_only=False,
        bake_anim=True,
        bake_anim_use_all_actions=False,
        bake_anim_use_nla_strips=False,
        bake_anim_simplify_factor=0.0,
        path_mode="AUTO",
    )
    if not path.is_file() or path.stat().st_size < 1024:
        raise RuntimeError("FBX export did not create a usable file")
    return exported


def main() -> None:
    args = parse_args()
    source = args.source.resolve()
    output_blend = args.output_blend.resolve()
    output_fbx = args.output_fbx.resolve()
    output_dir = args.output_dir.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if output_blend.exists() or output_fbx.exists() or output_dir.exists():
        raise FileExistsError("refusing to overwrite immutable v685 output")
    output_blend.parent.mkdir(parents=True, exist_ok=True)
    output_fbx.parent.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True)
    if Path(bpy.data.filepath).resolve() != source:
        bpy.ops.wm.open_mainfile(filepath=str(source))

    head = bpy.data.objects.get("head.")
    armature = bpy.data.objects.get("ARM")
    if head is None or head.type != "MESH" or armature is None or armature.type != "ARMATURE":
        raise RuntimeError("Ururu head or armature is missing")
    actuators = []
    for name in ACTUATORS:
        obj = bpy.data.objects.get(name)
        if obj is None or obj.type != "MESH":
            raise RuntimeError(f"missing v684 actuator: {name}")
        prepare_actuator(obj, armature)
        actuators.append(obj)
    metrics = join_head(head, actuators)
    if metrics["addedVertexCount"] != 450:
        raise RuntimeError(f"unexpected actuator vertex count after join: {metrics['addedVertexCount']}")
    if set(SHAPE_KEYS) - set(metrics["shapeKeys"]):
        raise RuntimeError(f"joined head lost required shape keys: {metrics['shapeKeys']}")

    renders = render_qa(output_dir)
    bpy.ops.wm.save_as_mainfile(filepath=str(output_blend))
    exported_objects = export_fbx(output_fbx, armature)
    report = {
        "schemaVersion": 1,
        "iteration": "v685",
        "status": "packaged-draft-single-head-morph-fbx",
        "source": str(source),
        "sourceSha256": sha256(source),
        "outputBlend": {"file": str(output_blend), "sha256": sha256(output_blend), "bytes": output_blend.stat().st_size},
        "outputFbx": {"file": str(output_fbx), "sha256": sha256(output_fbx), "bytes": output_fbx.stat().st_size},
        "head": metrics,
        "exportedObjects": exported_objects,
        "renders": renders,
        "hypothesis": "Joining actuator geometry into the skinned head with aligned shape-key names will produce one UE-importable facial Morph Target asset.",
        "decision": "draft pending post-join visual QA and UE morph inventory",
        "automaticApproval": False,
        "humanApproved": False,
        "productionReady": False,
    }
    (output_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"iteration": "v685", "shapeKeys": metrics["shapeKeys"], "fbxBytes": output_fbx.stat().st_size}))


if __name__ == "__main__":
    main()
