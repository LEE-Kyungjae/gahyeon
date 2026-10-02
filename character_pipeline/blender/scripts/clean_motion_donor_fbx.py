#!/usr/bin/env python3
"""Remove presentation/control geometry and rebake donor animation to integer frames."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import bpy


def parse_args() -> argparse.Namespace:
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("stand-sit", "narration"), required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args(values)


def import_fbx(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path))


def select_only(objects: list[bpy.types.Object]) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    for item in objects:
        item.hide_set(False)
        item.hide_viewport = False
        item.hide_render = False
        item.select_set(True)
    bpy.context.view_layer.objects.active = next(
        item for item in objects if item.type == "ARMATURE"
    )


def clean_stand_sit_scene() -> tuple[bpy.types.Object, list[bpy.types.Object], int, int]:
    armatures = [item for item in bpy.context.scene.objects if item.type == "ARMATURE"]
    if len(armatures) != 1:
        raise RuntimeError(f"expected one stand/sit armature, found {len(armatures)}")
    armature = armatures[0]
    meshes = [
        item for item in bpy.context.scene.objects
        if item.type == "MESH"
        and any(mod.type == "ARMATURE" and mod.object == armature for mod in item.modifiers)
        and len(item.data.polygons) > 100
    ]
    if [item.name for item in meshes] != ["meHumanMale.001"]:
        raise RuntimeError(f"unexpected stand/sit render meshes: {[item.name for item in meshes]}")
    action = armature.animation_data.action if armature.animation_data else None
    if action is None:
        raise RuntimeError("stand/sit armature has no active action")
    armature.name = "StandSit_Donor_Armature"
    armature.data.name = "StandSit_Donor_Skeleton"
    meshes[0].name = "StandSit_Donor_Body"
    start, end = (round(value) for value in action.frame_range)
    bpy.context.scene.render.fps = 24
    bpy.context.scene.frame_start = start
    bpy.context.scene.frame_end = end
    return armature, meshes, start, end


def clean_narration_scene() -> tuple[bpy.types.Object, list[bpy.types.Object], int, int]:
    armatures = [item for item in bpy.context.scene.objects if item.type == "ARMATURE"]
    if len(armatures) != 1:
        raise RuntimeError(f"expected one narration armature, found {len(armatures)}")
    armature = armatures[0]
    meshes = [
        item for item in bpy.context.scene.objects
        if item.type == "MESH"
        and any(mod.type == "ARMATURE" and mod.object == armature for mod in item.modifiers)
    ]
    if [item.name for item in meshes] != ["Wolf3D_Avatar"]:
        raise RuntimeError(f"unexpected narration render meshes: {[item.name for item in meshes]}")
    shape_keys = meshes[0].data.shape_keys
    if shape_keys is None or len(shape_keys.key_blocks) != 64:
        raise RuntimeError("narration donor must retain exactly 64 source shape keys")
    action = armature.animation_data.action if armature.animation_data else None
    if action is None:
        raise RuntimeError("narration armature has no active action")
    armature.name = "Narration_Donor_Armature"
    armature.data.name = "Narration_Donor_Skeleton"
    meshes[0].name = "Narration_Donor_Body"
    start, end = (round(value) for value in action.frame_range)
    bpy.context.scene.render.fps = 24
    bpy.context.scene.frame_start = start
    bpy.context.scene.frame_end = end
    return armature, meshes, start, end


def export_clean_donor_fbx(
    output: Path,
    armature: bpy.types.Object,
    meshes: list[bpy.types.Object],
    start: int,
    end: int,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(f"refusing to overwrite processed donor: {output}")
    select_only([armature, *meshes])
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
        path_mode="COPY",
        embed_textures=False,
    )
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError(f"FBX export failed: {output}")


def main() -> int:
    args = parse_args()
    import_fbx(args.input)
    if args.mode == "stand-sit":
        armature, meshes, start, end = clean_stand_sit_scene()
    else:
        armature, meshes, start, end = clean_narration_scene()
    export_clean_donor_fbx(args.output, armature, meshes, start, end)
    report = {
        "schemaVersion": 1,
        "mode": args.mode,
        "status": "processed-draft",
        "source": str(args.input.resolve()),
        "output": str(args.output.resolve()),
        "fps": bpy.context.scene.render.fps,
        "frameStart": start,
        "frameEnd": end,
        "armature": armature.name,
        "boneCount": len(armature.data.bones),
        "meshes": [
            {
                "name": item.name,
                "vertices": len(item.data.vertices),
                "polygons": len(item.data.polygons),
                "shapeKeys": len(item.data.shape_keys.key_blocks) if item.data.shape_keys else 0,
            }
            for item in meshes
        ],
        "removedControlGeometry": args.mode == "stand-sit",
        "humanApproved": False,
        "releaseEligible": False,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    if args.report.exists():
        raise FileExistsError(f"refusing to overwrite processing report: {args.report}")
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
