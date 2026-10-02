#!/usr/bin/env python3
"""Export the jaw sweep with skinned geometry so UE Interchange retains the take."""

import argparse
import json
from pathlib import Path
import sys

import bpy

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from build_hayley_face_axis_sweep import POSES, build_hayley_face_axis_sweep  # noqa: E402


def export_hayley_face_sweep_full_v390(output, armature):
    if output.exists():
        raise FileExistsError(f"refusing to overwrite full sweep FBX: {output}")
    meshes = [
        item for item in bpy.context.scene.objects
        if item.type == "MESH"
        and any(mod.type == "ARMATURE" and mod.object == armature for mod in item.modifiers)
    ]
    if not meshes:
        raise RuntimeError("Hayley sweep export has no skinned meshes")
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for item in (armature, *meshes):
        item.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.export_scene.fbx(
        filepath=str(output),
        use_selection=True,
        object_types={"ARMATURE", "MESH"},
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_ALL",
        add_leaf_bones=False,
        use_armature_deform_only=False,
        bake_anim=True,
        bake_anim_use_all_bones=True,
        bake_anim_use_nla_strips=False,
        bake_anim_use_all_actions=False,
        bake_anim_force_startend_keying=True,
        bake_anim_step=1.0,
        bake_anim_simplify_factor=0.0,
        path_mode="STRIP",
        embed_textures=False,
    )
    return meshes


def main():
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(values)
    if args.report.exists():
        raise FileExistsError(f"refusing to overwrite report: {args.report}")
    armature, action = build_hayley_face_axis_sweep(args.input)
    meshes = export_hayley_face_sweep_full_v390(args.output, armature)
    report = {
        "schemaVersion": 1,
        "iteration": "v390",
        "status": "authored-draft-full-mesh-jaw-axis-sweep",
        "source": str(args.input.resolve()),
        "output": str(args.output.resolve()),
        "action": action.name,
        "meshCount": len(meshes),
        "meshes": [item.name for item in meshes],
        "poses": [
            {"frame": frame, "label": label, "localEulerDegrees": degrees}
            for frame, label, degrees in POSES
        ],
        "humanApproved": False,
        "releaseEligible": False,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"meshCount": len(meshes), "output": str(args.output)}))


if __name__ == "__main__":
    main()
