"""Seal the v178 skin surface as a non-production UE 5.8 HEAD_ONLY target."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import bmesh
import bpy


def sha256_v179(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export_keentools_metahuman_input_v179() -> dict:
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--skin-material-index", type=int, default=0)
    args = parser.parse_args(values)
    output = args.output_dir.resolve()
    if output.exists() and any(output.iterdir()):
        raise RuntimeError(f"refusing to overwrite immutable v179 package: {output}")
    source_blend = Path(bpy.data.filepath).resolve()
    if not source_blend.is_file():
        raise RuntimeError("a saved normalized v178 Blender scene is required")
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if len(meshes) != 1:
        raise RuntimeError(f"expected one v178 reconstruction mesh, found {len(meshes)}")
    source = meshes[0]
    polygon_counts = {}
    for polygon in source.data.polygons:
        polygon_counts[str(polygon.material_index)] = polygon_counts.get(
            str(polygon.material_index), 0
        ) + 1
    if polygon_counts != {"0": 48004, "1": 1536, "2": 1536, "3": 8350}:
        raise RuntimeError(f"v178 primitive/material contract differs: {polygon_counts}")

    target = source.copy()
    target.data = source.data.copy()
    target.name = "Gahyeon_KeenTools_SkinTarget_v179"
    bpy.context.scene.collection.objects.link(target)
    bm = bmesh.new()
    bm.from_mesh(target.data)
    bm.faces.ensure_lookup_table()
    remove = [face for face in bm.faces if face.material_index != args.skin_material_index]
    bmesh.ops.delete(bm, geom=remove, context="FACES")
    loose = [vert for vert in bm.verts if not vert.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bm.to_mesh(target.data)
    bm.free()
    target.data.materials.clear()
    target.data.materials.append(source.data.materials[args.skin_material_index])
    target.data.update()
    bpy.context.view_layer.update()

    bm = bmesh.new()
    bm.from_mesh(target.data)
    boundary = sum(1 for edge in bm.edges if len(edge.link_faces) == 1)
    over_two = sum(1 for edge in bm.edges if len(edge.link_faces) > 2)
    loose_edges = sum(1 for edge in bm.edges if not edge.link_faces)
    bm.free()
    if len(target.data.vertices) < 20_000 or len(target.data.polygons) != 48_004:
        raise RuntimeError("isolated v179 skin topology is implausible")
    if over_two or loose_edges:
        raise RuntimeError(f"unsafe skin topology: overTwo={over_two}, loose={loose_edges}")

    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    source.hide_set(True)
    target.hide_set(False)
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    fbx = output / "gahyeon-keentools-skin-target-v179.fbx"
    bpy.ops.export_scene.fbx(
        filepath=str(fbx), use_selection=True, bake_anim=False, add_leaf_bones=False,
        mesh_smooth_type="FACE", axis_forward="Y", axis_up="Z",
        bake_space_transform=False, path_mode="COPY", embed_textures=False,
    )
    if not fbx.is_file() or fbx.stat().st_size < 100_000:
        raise RuntimeError("v179 FBX export failed")
    dimensions = [round(float(value), 6) for value in target.dimensions]
    manifest = {
        "schemaVersion": 1,
        "iteration": "v179",
        "state": "sealed-keentools-shape-target-awaiting-ue58-head-only-conform",
        "source": {"path": str(source_blend), "sha256": sha256_v179(source_blend)},
        "exporterSha256": sha256_v179(Path(__file__).resolve()),
        "isolation": {
            "method": "material-primitive-role",
            "retainedMaterialIndex": args.skin_material_index,
            "excludedRoles": ["left-eye", "right-eye", "teeth-and-oral-geometry"],
            "sourcePolygonCountsByMaterial": polygon_counts,
        },
        "topology": {
            "vertices": len(target.data.vertices), "polygons": len(target.data.polygons),
            "boundaryEdges": boundary, "nonManifoldEdgesOverTwoFaces": over_two,
            "looseEdges": loose_edges, "dimensionsCm": dimensions,
        },
        "files": [{"uri": fbx.name, "bytes": fbx.stat().st_size,
                   "sha256": sha256_v179(fbx)}],
        "claims": {
            "identityApproved": False, "metaHumanConformed": False,
            "productionTopology": False, "conformExperimentAuthorizedByUser": True,
            "productionReady": False,
        },
        "nextAction": "UE 5.8 HEAD_ONLY conform, then fixed-camera visual identity review",
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))
    return manifest


if __name__ == "__main__":
    export_keentools_metahuman_input_v179()
