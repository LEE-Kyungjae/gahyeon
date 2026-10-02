#!/usr/bin/env python3
"""Flip only Ururu's UE-culled eyelid/lash faces and export a new FBX."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import bmesh
import bpy


HEAD = "Ururu_Head_Facial_v685"
ARMATURE = "ARM"
ACTUATOR_MATERIALS = {"Ururu_EyelidSkin_v684", "Ururu_BlinkLash_v684"}
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


def average_normal(mesh: bpy.types.Mesh, material_indices: set[int]) -> list[float]:
    polygons = [polygon for polygon in mesh.polygons if polygon.material_index in material_indices]
    if not polygons:
        raise RuntimeError("eyelid actuator polygons are missing")
    return [sum(polygon.normal[axis] for polygon in polygons) / len(polygons) for axis in range(3)]


def repair_ururu_eyelid_winding_v733() -> None:
    args = parse_args()
    source = args.source.resolve()
    output_blend = args.output_blend.resolve()
    output_fbx = args.output_fbx.resolve()
    report_path = args.report.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if output_blend.exists() or output_fbx.exists() or report_path.exists():
        raise FileExistsError("refusing to overwrite immutable v733 output")
    output_blend.parent.mkdir(parents=True, exist_ok=True)
    output_fbx.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    if Path(bpy.data.filepath).resolve() != source:
        bpy.ops.wm.open_mainfile(filepath=str(source))

    head = bpy.data.objects.get(HEAD)
    armature = bpy.data.objects.get(ARMATURE)
    if head is None or head.type != "MESH" or armature is None or armature.type != "ARMATURE":
        raise RuntimeError("v688 head or armature is unavailable")
    materials = [material.name if material else None for material in head.data.materials]
    material_indices = {index for index, name in enumerate(materials) if name in ACTUATOR_MATERIALS}
    if len(material_indices) != len(ACTUATOR_MATERIALS):
        raise RuntimeError(f"unexpected eyelid material slots: {materials}")
    morphs = {key.name for key in head.data.shape_keys.key_blocks} if head.data.shape_keys else set()
    if not REQUIRED_MORPHS.issubset(morphs):
        raise RuntimeError(f"required morphs are missing: {sorted(REQUIRED_MORPHS - morphs)}")

    before = average_normal(head.data, material_indices)
    bm = bmesh.new()
    bm.from_mesh(head.data)
    selected = [face for face in bm.faces if face.material_index in material_indices]
    if len(selected) != 336:
        bm.free()
        raise RuntimeError(f"unexpected eyelid/lash face count: {len(selected)}")
    for face in selected:
        face.normal_flip()
    bm.to_mesh(head.data)
    bm.free()
    head.data.update()
    after = average_normal(head.data, material_indices)
    if before[1] <= 0.9 or after[1] >= -0.9:
        raise RuntimeError(f"eyelid normal repair failed: before={before}, after={after}")

    bpy.ops.wm.save_as_mainfile(filepath=str(output_blend))
    bpy.ops.object.select_all(action="DESELECT")
    exported = []
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH":
            obj.select_set(True)
            exported.append(obj.name)
    armature.select_set(True)
    exported.append(armature.name)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.export_scene.fbx(
        filepath=str(output_fbx),
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
    if not output_fbx.is_file() or output_fbx.stat().st_size < 1024:
        raise RuntimeError("v733 FBX export failed")
    report = {
        "schemaVersion": 1,
        "iteration": "v733",
        "status": "repaired-draft-eyelid-winding",
        "source": {"file": str(source), "sha256": sha256(source)},
        "outputBlend": {"file": str(output_blend), "sha256": sha256(output_blend)},
        "outputFbx": {"file": str(output_fbx), "sha256": sha256(output_fbx), "bytes": output_fbx.stat().st_size},
        "flippedFaceCount": len(selected),
        "materialSlots": sorted(material_indices),
        "averageNormalBefore": before,
        "averageNormalAfter": after,
        "morphTargets": sorted(REQUIRED_MORPHS),
        "exportedObjects": exported,
        "hypothesis": "The eyelid actuators disappear in Unreal because their +Y winding faces away from the -Y QA camera.",
        "action": "Flip only the eyelid and lash material faces while preserving all prior geometry, morphs, animation, and skeleton data.",
        "expectedResult": "UE renders the authored closed lids when EyeBlink_L and EyeBlink_R reach one.",
        "automaticApproval": False,
        "humanApproved": False,
        "productionReady": False,
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"iteration": "v733", "flippedFaceCount": len(selected), "outputFbx": str(output_fbx)}))


if __name__ == "__main__":
    repair_ururu_eyelid_winding_v733()
