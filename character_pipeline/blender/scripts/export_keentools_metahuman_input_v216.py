"""Export the retained v178 head surface with deterministic smooth normals."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import bmesh
import bpy


ITERATION = "v216"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def connected_material_components(mesh, material_index: int):
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table()
    remaining = {face for face in bm.faces if face.material_index == material_index}
    components = []
    while remaining:
        seed = remaining.pop()
        stack = [seed]
        component = {seed}
        while stack:
            face = stack.pop()
            for edge in face.edges:
                for linked in edge.link_faces:
                    if linked in remaining:
                        remaining.remove(linked)
                        component.add(linked)
                        stack.append(linked)
        components.append(component)
    components.sort(key=len, reverse=True)
    return bm, components


def export_keentools_metahuman_input_v216() -> dict:
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--skin-material-index", type=int, default=0)
    args = parser.parse_args(values)
    output = args.output_dir.resolve()
    if output.exists() and any(output.iterdir()):
        raise RuntimeError(f"refusing to overwrite immutable {ITERATION} package: {output}")

    source_blend = Path(bpy.data.filepath).resolve()
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not source_blend.is_file() or len(meshes) != 1:
        raise RuntimeError("a saved normalized v178 scene with one mesh is required")
    source = meshes[0]
    polygon_counts = {}
    for polygon in source.data.polygons:
        key = str(polygon.material_index)
        polygon_counts[key] = polygon_counts.get(key, 0) + 1
    expected_counts = {"0": 48004, "1": 1536, "2": 1536, "3": 8350}
    if polygon_counts != expected_counts:
        raise RuntimeError(f"v178 material contract differs: {polygon_counts}")

    target = source.copy()
    target.data = source.data.copy()
    target.name = "Gahyeon_KeenTools_SmoothHeadTarget_v216"
    bpy.context.scene.collection.objects.link(target)
    bm, components = connected_material_components(target.data, args.skin_material_index)
    component_sizes = [len(component) for component in components]
    if component_sizes[:3] != [45140, 1236, 1236]:
        bm.free()
        raise RuntimeError(f"v178 skin component contract differs: {component_sizes}")
    retained = components[0]
    bmesh.ops.delete(bm, geom=[face for face in bm.faces if face not in retained], context="FACES")
    loose = [vertex for vertex in bm.verts if not vertex.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(target.data)
    bm.free()

    target.data.materials.clear()
    target.data.materials.append(source.data.materials[args.skin_material_index])
    for polygon in target.data.polygons:
        polygon.use_smooth = True
    target.data.validate(clean_customdata=False)
    target.data.update(calc_edges=True)
    bpy.context.view_layer.update()

    audit = bmesh.new()
    audit.from_mesh(target.data)
    boundary = sum(1 for edge in audit.edges if len(edge.link_faces) == 1)
    over_two = sum(1 for edge in audit.edges if len(edge.link_faces) > 2)
    loose_edges = sum(1 for edge in audit.edges if not edge.link_faces)
    audit.free()
    smooth_polygons = sum(1 for polygon in target.data.polygons if polygon.use_smooth)
    if (len(target.data.vertices), len(target.data.polygons)) != (22808, 45140):
        raise RuntimeError("isolated v216 topology differs from the retained v181 surface")
    if smooth_polygons != len(target.data.polygons):
        raise RuntimeError(f"smooth-normal contract failed: {smooth_polygons}")
    if over_two or loose_edges:
        raise RuntimeError(f"unsafe topology: overTwo={over_two}, loose={loose_edges}")

    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    source.hide_set(True)
    target.hide_set(False)
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    fbx = output / "gahyeon-keentools-smooth-head-target-v216.fbx"
    bpy.ops.export_scene.fbx(
        filepath=str(fbx),
        use_selection=True,
        bake_anim=False,
        add_leaf_bones=False,
        mesh_smooth_type="OFF",
        use_mesh_modifiers=True,
        use_triangles=False,
        axis_forward="Y",
        axis_up="Z",
        bake_space_transform=False,
        path_mode="COPY",
        embed_textures=False,
    )
    if not fbx.is_file() or fbx.stat().st_size < 100_000:
        raise RuntimeError("v216 FBX export failed")

    manifest = {
        "schemaVersion": 1,
        "iteration": ITERATION,
        "state": "smooth-normal-head-target-awaiting-unreal-import-qa",
        "hypothesis": "Broken FBX smoothing corrupted the face-tracker portrait and produced invalid conform curves.",
        "source": {"path": str(source_blend), "sha256": sha256(source_blend)},
        "exporterSha256": sha256(Path(__file__).resolve()),
        "isolation": {
            "method": "material-role-plus-largest-edge-connected-surface",
            "retainedMaterialIndex": args.skin_material_index,
            "retainedConnectedComponentFaces": len(retained),
            "skinMaterialComponentFaceCounts": component_sizes,
            "sourcePolygonCountsByMaterial": polygon_counts,
        },
        "normalContract": {
            "recalculatedFaceNormals": True,
            "smoothPolygons": smooth_polygons,
            "allPolygonsSmooth": True,
            "fbxMeshSmoothType": "OFF",
        },
        "topology": {
            "vertices": len(target.data.vertices),
            "polygons": len(target.data.polygons),
            "boundaryEdges": boundary,
            "nonManifoldEdgesOverTwoFaces": over_two,
            "looseEdges": loose_edges,
            "dimensionsCm": [round(float(value), 6) for value in target.dimensions],
        },
        "files": [{"uri": fbx.name, "bytes": fbx.stat().st_size, "sha256": sha256(fbx)}],
        "claims": {
            "identityApproved": False,
            "metaHumanConformed": False,
            "productionTopology": False,
            "productionReady": False,
        },
        "nextAction": "Import as a new UE asset and reject unless the Unreal clay preview is smoothly readable.",
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False))
    return manifest


if __name__ == "__main__":
    export_keentools_metahuman_input_v216()
