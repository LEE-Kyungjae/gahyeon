#!/usr/bin/env python3
"""Bake textured Ururu's meter-authored rig and meshes into centimeter coordinates."""

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
    parser.add_argument("--output-blend", required=True, type=Path)
    parser.add_argument("--output-fbx", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    return parser.parse_args(values)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def apply_scale(obj) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    obj.hide_set(False)
    obj.hide_viewport = False
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    result = bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if "FINISHED" not in result:
        raise RuntimeError(f"failed to apply scale to {obj.name}: {result}")


def normalize_ururu_skeleton_units_v584(args: argparse.Namespace) -> dict[str, object]:
    if not args.source.is_file():
        raise FileNotFoundError(args.source)
    outputs = (args.output_blend, args.output_fbx, args.report)
    if any(path.exists() for path in outputs):
        raise FileExistsError("refusing to overwrite immutable v584 output")
    bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()))
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if len(armatures) != 1 or len(meshes) != 5:
        raise RuntimeError(f"unexpected Ururu structure: {len(armatures)} rigs/{len(meshes)} meshes")
    armature = armatures[0]
    pelvis_name = "ValveBiped.Bip01_Pelvis"
    pelvis = armature.data.bones.get(pelvis_name)
    if pelvis is None or len(armature.data.bones) != 179:
        raise RuntimeError("Ururu's expected 179-bone skeleton is unavailable")
    before = {
        "armatureHeight": float(armature.dimensions.z),
        "pelvisHeight": float(pelvis.head_local.z),
        "sceneScaleLength": float(bpy.context.scene.unit_settings.scale_length),
    }
    armature.scale = (100.0, 100.0, 100.0)
    apply_scale(armature)
    for mesh in meshes:
        apply_scale(mesh)
    units = bpy.context.scene.unit_settings
    units.system = "METRIC"
    units.scale_length = 0.01
    units.length_unit = "CENTIMETERS"
    pelvis = armature.data.bones[pelvis_name]
    if not 110.0 <= armature.dimensions.z <= 160.0:
        raise RuntimeError(f"normalized armature height is invalid: {armature.dimensions.z}")
    if not 65.0 <= pelvis.head_local.z <= 90.0:
        raise RuntimeError(f"normalized pelvis height is invalid: {pelvis.head_local.z}")
    for obj in [armature, *meshes]:
        if any(abs(value - 1.0) > 1e-4 for value in obj.scale):
            raise RuntimeError(f"unapplied scale remains on {obj.name}: {tuple(obj.scale)}")
    for mesh in meshes:
        modifiers = [modifier for modifier in mesh.modifiers if modifier.type == "ARMATURE"]
        if len(modifiers) != 1 or modifiers[0].object != armature:
            raise RuntimeError(f"invalid armature binding on {mesh.name}")
    for parent in {path.parent for path in outputs}:
        parent.mkdir(parents=True, exist_ok=False)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output_blend.resolve()), check_existing=False)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in [armature, *meshes]:
        obj.hide_set(False)
        obj.hide_viewport = False
        obj.hide_render = False
        obj.select_set(True)
    bpy.context.view_layer.objects.active = armature
    result = bpy.ops.export_scene.fbx(
        filepath=str(args.output_fbx.resolve()),
        use_selection=True,
        object_types={"ARMATURE", "MESH"},
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_UNITS",
        add_leaf_bones=False,
        bake_anim=False,
        path_mode="COPY",
        embed_textures=True,
    )
    if "FINISHED" not in result or args.output_fbx.stat().st_size < 1024:
        raise RuntimeError(f"normalized Ururu export failed: {result}")
    report = {
        "schemaVersion": 1,
        "iteration": "v584",
        "status": "normalized-draft-centimeter-skeleton",
        "source": {"file": str(args.source.resolve()), "sha256": sha256(args.source)},
        "output": {
            "blend": str(args.output_blend.resolve()),
            "blendSha256": sha256(args.output_blend),
            "fbx": str(args.output_fbx.resolve()),
            "fbxSha256": sha256(args.output_fbx),
        },
        "before": before,
        "after": {
            "armatureHeightCm": float(armature.dimensions.z),
            "pelvisHeightCm": float(pelvis.head_local.z),
            "sceneScaleLength": float(units.scale_length),
            "boneCount": len(armature.data.bones),
            "meshCount": len(meshes),
        },
        "hypothesis": "Baking Ururu into centimeter coordinates will preserve full scale during UE IK retargeting.",
        "visualValidationPending": True,
        "humanApproved": False,
        "releaseEligible": False,
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    print(json.dumps(normalize_ururu_skeleton_units_v584(parse_args()), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
