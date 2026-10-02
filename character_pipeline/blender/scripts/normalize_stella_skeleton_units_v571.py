#!/usr/bin/env python3
"""Bake Stella/Lily's meter-authored rig and meshes into centimeter coordinates."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy


EXCLUDED_PREVIEW_MESHES = {
    "MI_CH_NPC_Lilly_Eyeshadow",
    "MI_CH_NPC_Lilly_Eyeshadow2",
    "MI_Tearline_Lily",
    "NewMaterial",
}


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


def normalize_stella_skeleton_units_v571(args: argparse.Namespace) -> dict[str, object]:
    if not args.source.is_file():
        raise FileNotFoundError(args.source)
    outputs = (args.output_blend, args.output_fbx, args.report)
    if any(path.exists() for path in outputs):
        raise FileExistsError("refusing to overwrite immutable v571 output")

    bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()))
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if len(armatures) != 1 or len(meshes) != 13:
        raise RuntimeError(f"unexpected Stella structure: {len(armatures)} rigs/{len(meshes)} meshes")
    armature = armatures[0]
    pelvis = armature.data.bones.get("Bip001-Pelvis")
    if pelvis is None or len(armature.data.bones) != 219:
        raise RuntimeError("Stella's expected 219-bone Bip001 skeleton is unavailable")

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

    pelvis = armature.data.bones["Bip001-Pelvis"]
    if not 150.0 <= armature.dimensions.z <= 180.0:
        raise RuntimeError(f"normalized armature height is invalid: {armature.dimensions.z}")
    if not 80.0 <= pelvis.head_local.z <= 100.0:
        raise RuntimeError(f"normalized pelvis height is invalid: {pelvis.head_local.z}")
    for obj in [armature, *meshes]:
        if any(abs(value - 1.0) > 1e-4 for value in obj.scale):
            raise RuntimeError(f"unapplied scale remains on {obj.name}: {tuple(obj.scale)}")
    for mesh in meshes:
        armature_modifiers = [modifier for modifier in mesh.modifiers if modifier.type == "ARMATURE"]
        if len(armature_modifiers) != 1 or armature_modifiers[0].object != armature:
            raise RuntimeError(f"invalid armature binding on {mesh.name}")

    for parent in {path.parent for path in outputs}:
        parent.mkdir(parents=True, exist_ok=False)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output_blend.resolve()), check_existing=False)

    export_meshes = [mesh for mesh in meshes if mesh.name not in EXCLUDED_PREVIEW_MESHES]
    bpy.ops.object.select_all(action="DESELECT")
    for obj in [armature, *export_meshes]:
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
        raise RuntimeError(f"normalized Stella export failed: {result}")

    report = {
        "schemaVersion": 1,
        "iteration": "v571",
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
            "previewMeshCount": len(export_meshes),
        },
        "previewExcludedMeshes": sorted(EXCLUDED_PREVIEW_MESHES),
        "hypothesis": "Baking Stella's meter-authored armature and meshes into centimeter coordinates will stop UE IK Retargeter from emitting 1/100-scale bone translations.",
        "visualValidationPending": True,
        "humanApproved": False,
        "releaseEligible": False,
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    report = normalize_stella_skeleton_units_v571(parse_args())
    print("STELLA_UNIT_NORMALIZATION=" + json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
