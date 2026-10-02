#!/usr/bin/env python3
"""Export Ururu Morph Targets without an FBX animation stack."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy


REQUIRED = {"EyeBlink_L", "EyeBlink_R", "GazeLeft", "GazeRight"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
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


def main() -> None:
    args = parse_args()
    source = args.source.resolve()
    output_fbx = args.output_fbx.resolve()
    report_path = args.report.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if output_fbx.exists() or report_path.exists():
        raise FileExistsError("refusing to overwrite immutable v691 output")
    for parent in {output_fbx.parent, report_path.parent}:
        parent.mkdir(parents=True, exist_ok=False)
    if Path(bpy.data.filepath).resolve() != source:
        bpy.ops.wm.open_mainfile(filepath=str(source))
    head = bpy.data.objects.get("Ururu_Head_Facial_v685")
    armature = bpy.data.objects.get("ARM")
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if head is None or armature is None or len(meshes) != 5 or head.data.shape_keys is None:
        raise RuntimeError("v688 facial mesh structure is incomplete")
    morphs = {key.name for key in head.data.shape_keys.key_blocks}
    if REQUIRED - morphs:
        raise RuntimeError(f"v688 is missing Morph Targets: {sorted(REQUIRED - morphs)}")
    bpy.context.scene.frame_set(1)
    for action_owner in (head.data.shape_keys, armature):
        if action_owner.animation_data is not None:
            action_owner.animation_data_clear()
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
        mesh_smooth_type="FACE",
        add_leaf_bones=False,
        bake_anim=False,
        path_mode="AUTO",
    )
    if "FINISHED" not in result or not output_fbx.is_file() or output_fbx.stat().st_size < 1024:
        raise RuntimeError(f"static Morph Target FBX export failed: {result}")
    report = {
        "schemaVersion": 1,
        "iteration": "v691",
        "status": "exported-static-fbx-with-morph-targets",
        "source": {"file": str(source), "sha256": sha256(source)},
        "outputFbx": {"file": str(output_fbx), "sha256": sha256(output_fbx), "bytes": output_fbx.stat().st_size},
        "morphTargets": sorted(REQUIRED),
        "boneCount": len(armature.data.bones),
        "meshCount": len(meshes),
        "fbxAnimationExported": False,
        "hypothesis": "Removing the FBX animation stack will let UE bind the Morph Target mesh to the validated v585 skeleton instead of creating a new animation skeleton.",
        "decision": "draft pending UE import",
        "automaticApproval": False,
        "humanApproved": False,
        "productionReady": False,
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"iteration": "v691", "fbxBytes": output_fbx.stat().st_size, "morphTargets": sorted(REQUIRED)}))


if __name__ == "__main__":
    main()
