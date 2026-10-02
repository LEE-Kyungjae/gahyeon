#!/usr/bin/env python3
"""Export Hayley in the verified Blender bind pose without the corrupt embedded take."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy


def parse_args() -> argparse.Namespace:
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    return parser.parse_args(values)


def build_clean_hayley_bind_pose_v447(source: Path, output: Path, report_path: Path) -> dict[str, object]:
    if not source.is_file():
        raise FileNotFoundError(source)
    for destination in (output, report_path):
        if destination.exists():
            raise FileExistsError(f"refusing to overwrite immutable output: {destination}")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(source))
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    if len(armatures) != 1:
        raise RuntimeError(f"expected one armature, found {len(armatures)}")
    armature = armatures[0]
    render_meshes = [
        obj for obj in bpy.context.scene.objects
        if obj.type == "MESH"
        and len(obj.data.polygons) > 100
        and any(mod.type == "ARMATURE" and mod.object == armature for mod in obj.modifiers)
    ]
    if len(render_meshes) < 6:
        raise RuntimeError(f"unexpected render mesh inventory: {[obj.name for obj in render_meshes]}")

    removed_actions = sorted(action.name for action in bpy.data.actions)
    armature.data.pose_position = "REST"
    armature.animation_data_clear()
    for obj in bpy.context.scene.objects:
        if obj.animation_data:
            obj.animation_data_clear()
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = 1
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()

    bpy.ops.object.select_all(action="DESELECT")
    for obj in [armature, *render_meshes]:
        obj.hide_set(False)
        obj.hide_viewport = False
        obj.hide_render = False
        obj.select_set(True)
    bpy.context.view_layer.objects.active = armature

    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.fbx(
        filepath=str(output),
        use_selection=True,
        object_types={"ARMATURE", "MESH"},
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_ALL",
        add_leaf_bones=False,
        use_armature_deform_only=False,
        bake_anim=False,
        path_mode="COPY",
        embed_textures=False,
    )
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError("clean FBX export failed")

    report = {
        "schemaVersion": 1,
        "iteration": "v447",
        "status": "processed-draft-bind-pose-only",
        "hypothesis": "Removing Hayley's corrupt embedded take will make Unreal import the verified A-pose as its stable reference pose.",
        "source": {
            "file": str(source.resolve()),
            "bytes": source.stat().st_size,
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        },
        "output": {
            "file": str(output.resolve()),
            "bytes": output.stat().st_size,
            "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        },
        "armature": armature.name,
        "boneCount": len(armature.data.bones),
        "removedActions": removed_actions,
        "meshes": [
            {
                "name": obj.name,
                "vertices": len(obj.data.vertices),
                "polygons": len(obj.data.polygons),
                "materials": [slot.material.name if slot.material else None for slot in obj.material_slots],
            }
            for obj in render_meshes
        ],
        "humanApproved": False,
        "releaseEligible": False,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    args = parse_args()
    report = build_clean_hayley_bind_pose_v447(args.input, args.output, args.report)
    print(json.dumps({
        "iteration": report["iteration"],
        "boneCount": report["boneCount"],
        "meshCount": len(report["meshes"]),
        "removedActions": report["removedActions"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
