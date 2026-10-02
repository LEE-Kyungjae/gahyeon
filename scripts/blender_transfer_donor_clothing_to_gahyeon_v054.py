"""Conform separated donor clothing to the current Gahyeon MetaHuman body."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils.bvhtree import BVHTree


def arguments():
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-body", required=True, type=Path)
    parser.add_argument("--output-blend", required=True, type=Path)
    parser.add_argument("--output-top", required=True, type=Path)
    parser.add_argument("--output-bottom", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    return parser.parse_args(values)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def points(obj):
    return [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]


def z_bounds(obj):
    values = [point.z for point in points(obj)]
    return min(values), max(values)


def export_object(obj, path):
    for candidate in bpy.data.objects:
        candidate.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.fbx(
        filepath=str(path.resolve()),
        use_selection=True,
        object_types={"MESH"},
        use_mesh_modifiers=True,
        add_leaf_bones=False,
        bake_anim=False,
        path_mode="COPY",
        embed_textures=True,
    )


args = arguments()
source_scene = Path(bpy.data.filepath).resolve()
for source in (source_scene, args.target_body):
    if not source.is_file():
        raise RuntimeError(f"missing transfer source: {source}")
for output in (args.output_blend, args.output_top, args.output_bottom, args.report):
    if output.exists():
        raise RuntimeError(f"refusing to overwrite v054 output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

donor_body = bpy.data.objects.get("Body")
top = bpy.data.objects.get("top_cloth")
bottom = bpy.data.objects.get("bottome")
if not donor_body or not top or not bottom:
    raise RuntimeError("extracted donor body/top/bottom are unavailable")

before = set(bpy.data.objects)
bpy.ops.wm.fbx_import(filepath=str(args.target_body), use_anim=False)
imported = [obj for obj in bpy.data.objects if obj not in before]
target = next(obj for obj in imported if obj.type == "MESH" and obj.name.endswith("LOD0"))

donor_min_z, donor_max_z = z_bounds(donor_body)
target_min_z, target_max_z = z_bounds(target)
scale = (target_max_z - target_min_z) / (donor_max_z - donor_min_z)
target_surface = BVHTree.FromPolygons(
    points(target), [tuple(polygon.vertices) for polygon in target.data.polygons], all_triangles=False
)

results = {}
for garment, clearance_cm, output_name in (
    (top, 0.8, "SM_Gahyeon_DonorTop_v054"),
    (bottom, 1.2, "SM_Gahyeon_DonorBottom_v054"),
):
    inverse = garment.matrix_world.inverted()
    movements = []
    for vertex in garment.data.vertices:
        world = garment.matrix_world @ vertex.co
        normalized = world.copy()
        normalized.x *= scale
        normalized.y *= scale
        normalized.z = target_min_z + (world.z - donor_min_z) * scale
        nearest, normal, _, _ = target_surface.find_nearest(normalized)
        if nearest is None or normal is None:
            raise RuntimeError(f"no target surface for {garment.name} vertex {vertex.index}")
        normal.normalize()
        conformed = nearest + normal * (clearance_cm / 100.0)
        movements.append((conformed - normalized).length * 100.0)
        vertex.co = inverse @ conformed
    garment.name = output_name
    garment.data.name = f"{output_name}_Mesh"
    garment["gahyeon_iteration"] = "v054"
    garment["source_scale"] = scale
    garment["surface_clearance_cm"] = clearance_cm
    # Static geometry proof only: remove donor-rig deformation before export.
    for modifier in list(garment.modifiers):
        if modifier.type == "ARMATURE":
            garment.modifiers.remove(modifier)
    garment.parent = None
    results[output_name] = {
        "vertices": len(garment.data.vertices),
        "polygons": len(garment.data.polygons),
        "clearanceCm": clearance_cm,
        "movementCm": {"mean": sum(movements) / len(movements), "max": max(movements)},
    }

keep = {top, bottom, target}
for obj in list(bpy.data.objects):
    if obj not in keep:
        bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=str(args.output_blend.resolve()))
export_object(top, args.output_top)
export_object(bottom, args.output_bottom)

report = {
    "schemaVersion": 1,
    "iteration": "v054",
    "state": "static-transfer-poc",
    "productionReady": False,
    "hypothesis": "Height-normalized donor garments can be surface-conformed to the MetaHuman body before investing in skin-weight transfer.",
    "inputs": {
        "donorBlend": {"file": str(source_scene), "sha256": sha256(source_scene)},
        "targetBody": {"file": str(args.target_body.resolve()), "sha256": sha256(args.target_body)},
    },
    "normalization": {
        "donorHeightMeters": donor_max_z - donor_min_z,
        "targetHeightMeters": target_max_z - target_min_z,
        "uniformScale": scale,
    },
    "garments": results,
    "outputs": {
        "blend": {"file": str(args.output_blend.resolve()), "sha256": sha256(args.output_blend)},
        "topFbx": {"file": str(args.output_top.resolve()), "sha256": sha256(args.output_top)},
        "bottomFbx": {"file": str(args.output_bottom.resolve()), "sha256": sha256(args.output_bottom)},
    },
    "nextGate": "Render both garments on the current MetaHuman and reject if silhouette, openings, or body clearance fail.",
}
args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
