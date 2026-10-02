#!/usr/bin/env python3
"""Export an immutable modular skeletal-character FBX for Unreal POC import."""

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
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--iteration", default="v516")
    return parser.parse_args(values)


def export_character_candidate_v516(
    source: Path, output: Path, report_path: Path, iteration: str
) -> dict[str, object]:
    if not source.is_file():
        raise FileNotFoundError(source)
    if output.exists() or report_path.exists():
        raise FileExistsError("refusing to overwrite immutable candidate export")

    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    meshes = [
        obj for obj in bpy.context.scene.objects
        if obj.type == "MESH" and not obj.hide_render and len(obj.data.polygons) > 40
    ]
    if len(armatures) != 1 or not meshes:
        raise RuntimeError(f"expected one rig and visible modular meshes, got {len(armatures)}/{len(meshes)}")
    armature = armatures[0]
    unbound = [
        mesh.name for mesh in meshes
        if not any(mod.type == "ARMATURE" and mod.object == armature for mod in mesh.modifiers)
    ]
    if unbound:
        raise RuntimeError(f"unbound renderable meshes: {unbound}")

    bpy.ops.object.select_all(action="DESELECT")
    armature.hide_set(False)
    armature.hide_viewport = False
    armature.select_set(True)
    for mesh in meshes:
        mesh.hide_set(False)
        mesh.hide_viewport = False
        mesh.select_set(True)
    bpy.context.view_layer.objects.active = armature

    output.parent.mkdir(parents=True, exist_ok=True)
    result = bpy.ops.export_scene.fbx(
        filepath=str(output.resolve()),
        use_selection=True,
        object_types={"ARMATURE", "MESH"},
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_UNITS",
        axis_forward="-Y",
        axis_up="Z",
        add_leaf_bones=False,
        use_armature_deform_only=False,
        bake_anim=False,
        path_mode="COPY",
        embed_textures=False,
    )
    if "FINISHED" not in result or not output.is_file() or output.stat().st_size < 1024:
        raise RuntimeError(f"FBX export failed: {result}")

    report = {
        "schemaVersion": 1,
        "iteration": iteration,
        "status": "exported-draft-modular-character",
        "source": {
            "file": str(source.resolve()),
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        },
        "output": {
            "file": str(output.resolve()),
            "bytes": output.stat().st_size,
            "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        },
        "armature": {"name": armature.name, "boneCount": len(armature.data.bones)},
        "meshes": [
            {
                "name": mesh.name,
                "vertices": len(mesh.data.vertices),
                "polygons": len(mesh.data.polygons),
                "materials": [slot.material.name if slot.material else None for slot in mesh.material_slots],
            }
            for mesh in meshes
        ],
        "modularMeshesPreserved": True,
        "humanApproved": False,
        "releaseEligible": False,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    args = parse_args()
    report = export_character_candidate_v516(args.source, args.output, args.report, args.iteration)
    print(json.dumps({"iteration": report["iteration"], "meshCount": len(report["meshes"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
