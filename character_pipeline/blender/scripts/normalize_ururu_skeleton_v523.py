#!/usr/bin/env python3
"""Replace Ururu's unweighted orphan root chain with one UE-safe root bone."""

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
    return parser.parse_args(values)


def normalize_ururu_skeleton_v523(source: Path, output: Path, report_path: Path) -> dict[str, object]:
    if not source.is_file():
        raise FileNotFoundError(source)
    if output.exists() or report_path.exists():
        raise FileExistsError("refusing to overwrite immutable Ururu normalization")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(source.resolve()))
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH" and len(obj.data.polygons) > 40]
    if len(armatures) != 1 or len(meshes) != 5:
        raise RuntimeError(f"unexpected Ururu structure: {len(armatures)} rigs/{len(meshes)} meshes")
    armature = armatures[0]
    original_roots = sorted(bone.name for bone in armature.data.bones if bone.parent is None)
    if original_roots != ["Armature", "ValveBiped.Bip01_Pelvis"]:
        raise RuntimeError(f"unexpected Ururu roots: {original_roots}")
    weighted_names = {
        group.name
        for mesh in meshes
        for group in mesh.vertex_groups
        if any(
            weight.group == group.index and weight.weight > 0.0
            for vertex in mesh.data.vertices
            for weight in vertex.groups
        )
    }
    if {"Armature", "Armature_end"} & weighted_names:
        raise RuntimeError("refusing to remove a weighted orphan root chain")

    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    edit_bones = armature.data.edit_bones
    orphan = edit_bones.get("Armature")
    orphan_end = edit_bones.get("Armature_end")
    pelvis = edit_bones.get("ValveBiped.Bip01_Pelvis")
    if orphan is None or orphan_end is None or pelvis is None:
        raise RuntimeError("required Ururu root bones are unavailable")
    edit_bones.remove(orphan_end)
    edit_bones.remove(orphan)
    root = edit_bones.new("root")
    root.head = (0.0, 0.0, 0.0)
    root.tail = (0.0, 0.0, 0.1)
    root.use_deform = False
    pelvis.parent = root
    pelvis.use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")

    normalized_roots = sorted(bone.name for bone in armature.data.bones if bone.parent is None)
    if normalized_roots != ["root"] or len(armature.data.bones) != 179:
        raise RuntimeError(f"root normalization failed: {normalized_roots}/{len(armature.data.bones)}")

    bpy.ops.object.select_all(action="DESELECT")
    armature.select_set(True)
    for mesh in meshes:
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
        raise RuntimeError(f"Ururu export failed: {result}")

    report = {
        "schemaVersion": 1,
        "iteration": "v523",
        "status": "normalized-draft-single-root-character",
        "source": {"file": str(source.resolve()), "sha256": hashlib.sha256(source.read_bytes()).hexdigest()},
        "output": {
            "file": str(output.resolve()),
            "bytes": output.stat().st_size,
            "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        },
        "meshCount": len(meshes),
        "originalBoneCount": 180,
        "normalizedBoneCount": 179,
        "originalRoots": original_roots,
        "normalizedRoots": normalized_roots,
        "removedUnweightedBones": ["Armature", "Armature_end"],
        "addedNonDeformRoot": "root",
        "humanApproved": False,
        "releaseEligible": False,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    args = parse_args()
    report = normalize_ururu_skeleton_v523(args.source, args.output, args.report)
    print(json.dumps({"iteration": report["iteration"], "roots": report["normalizedRoots"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
