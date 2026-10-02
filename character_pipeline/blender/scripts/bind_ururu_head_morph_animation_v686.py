#!/usr/bin/env python3
"""Bind and verify animation on Ururu's joined v685 head morph targets."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy


FRAMES = (("neutral", 1), ("blink", 10), ("gaze-screen-left", 20), ("gaze-screen-right", 30))
KEYS = ("GazeLeft", "GazeRight", "EyeBlink_L", "EyeBlink_R")


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


def bind_keys(head: bpy.types.Object) -> dict:
    blocks = head.data.shape_keys.key_blocks
    missing = set(KEYS) - {key.name for key in blocks}
    if missing:
        raise RuntimeError(f"v685 joined head is missing morphs: {sorted(missing)}")
    for name in KEYS:
        key = blocks[name]
        for _, frame in FRAMES:
            key.value = 0.0
            key.keyframe_insert(data_path="value", frame=frame)
    blocks["EyeBlink_L"].value = 1.0
    blocks["EyeBlink_L"].keyframe_insert(data_path="value", frame=10)
    blocks["EyeBlink_R"].value = 1.0
    blocks["EyeBlink_R"].keyframe_insert(data_path="value", frame=10)
    blocks["GazeLeft"].value = 1.0
    blocks["GazeLeft"].keyframe_insert(data_path="value", frame=20)
    blocks["GazeRight"].value = 1.0
    blocks["GazeRight"].keyframe_insert(data_path="value", frame=30)
    basis = blocks["Basis"]
    return {
        key.name: {
            "changedVertexCount": sum(
                (key.data[index].co - basis.data[index].co).length > 1e-8
                for index in range(len(basis.data))
            ),
            "maxDeltaMeters": max(
                (key.data[index].co - basis.data[index].co).length
                for index in range(len(basis.data))
            ),
        }
        for key in blocks
        if key.name != "Basis"
    }


def export_fbx(path: Path, armature: bpy.types.Object) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH":
            obj.select_set(True)
    armature.select_set(True)
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
        raise RuntimeError("v686 FBX export failed")


def main() -> None:
    args = parse_args()
    source = args.source.resolve()
    output_blend = args.output_blend.resolve()
    output_fbx = args.output_fbx.resolve()
    output_dir = args.output_dir.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if output_blend.exists() or output_fbx.exists() or output_dir.exists():
        raise FileExistsError("refusing to overwrite immutable v686 output")
    output_blend.parent.mkdir(parents=True, exist_ok=True)
    output_fbx.parent.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True)
    if Path(bpy.data.filepath).resolve() != source:
        bpy.ops.wm.open_mainfile(filepath=str(source))
    head = bpy.data.objects.get("Ururu_Head_Facial_v685")
    armature = bpy.data.objects.get("ARM")
    camera = bpy.data.objects.get("UruruRefinedEyelidCamera_v684")
    if head is None or armature is None or camera is None:
        raise RuntimeError("v685 head, armature, or sealed camera is missing")
    metrics = bind_keys(head)
    scene = bpy.context.scene
    scene.camera = camera
    renders = []
    for pose, frame in FRAMES:
        scene.frame_set(frame)
        path = output_dir / f"{pose}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        renders.append({"pose": pose, "frame": frame, "file": str(path), "sha256": sha256(path)})
    if renders[0]["sha256"] == renders[1]["sha256"]:
        raise RuntimeError("blink render is byte-identical to neutral after rebinding")
    bpy.ops.wm.save_as_mainfile(filepath=str(output_blend))
    export_fbx(output_fbx, armature)
    report = {
        "schemaVersion": 1,
        "iteration": "v686",
        "status": "packaged-draft-bound-head-morph-animation",
        "source": str(source),
        "sourceSha256": sha256(source),
        "outputBlend": {"file": str(output_blend), "sha256": sha256(output_blend), "bytes": output_blend.stat().st_size},
        "outputFbx": {"file": str(output_fbx), "sha256": sha256(output_fbx), "bytes": output_fbx.stat().st_size},
        "morphMetrics": metrics,
        "renders": renders,
        "decision": "draft pending direct visual QA and UE import morph inventory",
        "automaticApproval": False,
        "humanApproved": False,
        "productionReady": False,
    }
    (output_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"iteration": "v686", "morphs": list(metrics), "fbxBytes": output_fbx.stat().st_size}))


if __name__ == "__main__":
    main()
