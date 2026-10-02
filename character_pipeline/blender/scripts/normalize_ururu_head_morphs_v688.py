#!/usr/bin/env python3
"""Normalize Ururu's joined facial Morph Target asset to the validated cm rig."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy


REQUIRED_MORPHS = {"EyeBlink_L", "EyeBlink_R", "GazeLeft", "GazeRight"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output-blend", required=True, type=Path)
    parser.add_argument("--output-fbx", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(values)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def apply_scale(obj: bpy.types.Object) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    obj.hide_set(False)
    obj.hide_viewport = False
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    result = bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if "FINISHED" not in result:
        raise RuntimeError(f"failed to apply scale to {obj.name}: {result}")


def main() -> None:
    args = parse_args()
    source = args.source.resolve()
    output_blend = args.output_blend.resolve()
    output_fbx = args.output_fbx.resolve()
    report_path = args.report.resolve()
    outputs = (output_blend, output_fbx, report_path)
    if not source.is_file():
        raise FileNotFoundError(source)
    if any(path.exists() for path in outputs):
        raise FileExistsError("refusing to overwrite immutable v688 output")
    for parent in {path.parent for path in outputs}:
        parent.mkdir(parents=True, exist_ok=False)
    if Path(bpy.data.filepath).resolve() != source:
        bpy.ops.wm.open_mainfile(filepath=str(source))
    scene = bpy.context.scene
    scene.frame_set(1)
    armatures = [obj for obj in scene.objects if obj.type == "ARMATURE"]
    meshes = [obj for obj in scene.objects if obj.type == "MESH"]
    if len(armatures) != 1 or len(meshes) != 5:
        raise RuntimeError(f"unexpected v686 structure: {len(armatures)} rigs/{len(meshes)} meshes")
    armature = armatures[0]
    head = bpy.data.objects.get("Ururu_Head_Facial_v685")
    if head is None or head.data.shape_keys is None:
        raise RuntimeError("v686 joined facial head or Morph Targets are missing")
    morphs = {key.name for key in head.data.shape_keys.key_blocks}
    if REQUIRED_MORPHS - morphs:
        raise RuntimeError(f"v686 is missing required Morph Targets: {sorted(REQUIRED_MORPHS - morphs)}")
    pelvis = armature.data.bones.get("ValveBiped.Bip01_Pelvis")
    if pelvis is None or len(armature.data.bones) != 179:
        raise RuntimeError("Ururu's expected 179-bone skeleton is unavailable")
    before = {
        "armatureHeightMeters": float(armature.dimensions.z),
        "pelvisHeightMeters": float(pelvis.head_local.z),
        "sceneScaleLength": float(scene.unit_settings.scale_length),
    }
    armature.scale = (100.0, 100.0, 100.0)
    apply_scale(armature)
    for mesh in meshes:
        apply_scale(mesh)
    units = scene.unit_settings
    units.system = "METRIC"
    units.scale_length = 0.01
    units.length_unit = "CENTIMETERS"
    pelvis = armature.data.bones["ValveBiped.Bip01_Pelvis"]
    if not 110.0 <= armature.dimensions.z <= 160.0:
        raise RuntimeError(f"normalized armature height is invalid: {armature.dimensions.z}")
    if not 65.0 <= pelvis.head_local.z <= 90.0:
        raise RuntimeError(f"normalized pelvis height is invalid: {pelvis.head_local.z}")
    for obj in (armature, *meshes):
        if any(abs(value - 1.0) > 1e-4 for value in obj.scale):
            raise RuntimeError(f"unapplied scale remains on {obj.name}: {tuple(obj.scale)}")
    for mesh in meshes:
        modifiers = [modifier for modifier in mesh.modifiers if modifier.type == "ARMATURE"]
        if len(modifiers) != 1 or modifiers[0].object != armature:
            raise RuntimeError(f"invalid armature binding on {mesh.name}")

    bpy.ops.wm.save_as_mainfile(filepath=str(output_blend), check_existing=False)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in (armature, *meshes):
        obj.hide_set(False)
        obj.hide_viewport = False
        obj.hide_render = False
        obj.select_set(True)
    bpy.context.view_layer.objects.active = armature
    result = bpy.ops.export_scene.fbx(
        filepath=str(output_fbx),
        use_selection=True,
        object_types={"ARMATURE", "MESH"},
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_UNITS",
        use_mesh_modifiers=False,
        add_leaf_bones=False,
        bake_anim=True,
        bake_anim_use_all_actions=False,
        bake_anim_use_nla_strips=False,
        bake_anim_simplify_factor=0.0,
        path_mode="AUTO",
    )
    if "FINISHED" not in result or not output_fbx.is_file() or output_fbx.stat().st_size < 1024:
        raise RuntimeError(f"v688 normalized FBX export failed: {result}")
    report = {
        "schemaVersion": 1,
        "iteration": "v688",
        "status": "normalized-draft-centimeter-facial-morph-skeleton",
        "source": {"file": str(source), "sha256": sha256(source)},
        "output": {
            "blend": str(output_blend),
            "blendSha256": sha256(output_blend),
            "fbx": str(output_fbx),
            "fbxSha256": sha256(output_fbx),
            "fbxBytes": output_fbx.stat().st_size,
        },
        "before": before,
        "after": {
            "armatureHeightCm": float(armature.dimensions.z),
            "pelvisHeightCm": float(pelvis.head_local.z),
            "sceneScaleLength": float(units.scale_length),
            "boneCount": len(armature.data.bones),
            "meshCount": len(meshes),
            "morphTargets": sorted(REQUIRED_MORPHS),
        },
        "hypothesis": "Applying the validated v584 centimeter normalization to v686 will make its rest skeleton acceptable to the v585 UE skeleton.",
        "decision": "draft pending rest-skeleton hash comparison and UE import",
        "automaticApproval": False,
        "humanApproved": False,
        "productionReady": False,
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"iteration": "v688", "armatureHeightCm": report["after"]["armatureHeightCm"], "fbxBytes": output_fbx.stat().st_size}))


if __name__ == "__main__":
    main()
