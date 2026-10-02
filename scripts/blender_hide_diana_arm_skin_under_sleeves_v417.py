"""Remove only Diana's arm skin hidden by the jacket sleeves, preserving hands."""

import argparse
import json
from pathlib import Path

import bpy


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args, _ = parser.parse_known_args()

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.wm.fbx_import(filepath=str(args.input.resolve()))
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if len(meshes) != 1:
        raise RuntimeError(f"expected one mesh, found {[obj.name for obj in meshes]}")
    obj = meshes[0]
    mesh = obj.data
    hand_slot = next(i for i, material in enumerate(mesh.materials) if material and material.name == "ch0100_00_Hand")

    # The jacket cuff reaches |X| ~= 42.6 cm. Keep a generous hidden overlap and
    # preserve the visible wrist/hand from |X| >= 40 cm onward.
    remove = [
        polygon.index
        for polygon in mesh.polygons
        if polygon.material_index == hand_slot
        and max(abs(mesh.vertices[index].co.x) for index in polygon.vertices) < 40.0
    ]
    if not remove:
        raise RuntimeError("arm occlusion selection was empty")
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.object.mode_set(mode="OBJECT")
    for index in remove:
        mesh.polygons[index].select = True
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.delete(type="FACE")
    bpy.ops.object.mode_set(mode="OBJECT")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.fbx(
        filepath=str(args.output.resolve()),
        use_selection=False,
        bake_anim=False,
        add_leaf_bones=False,
        use_armature_deform_only=False,
    )
    report = {
        "schemaVersion": 1,
        "iteration": "v417-diana-shoulder-shell-clearance",
        "method": "delete hand-material faces fully beneath jacket cuff boundary",
        "material": "ch0100_00_Hand",
        "materialIndex": hand_slot,
        "removedFaces": len(remove),
        "keepBoundaryAbsXCentimeters": 40.0,
        "productionReady": False,
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
