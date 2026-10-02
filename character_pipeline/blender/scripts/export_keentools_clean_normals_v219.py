"""Export v178's retained head after removing corrupted custom split normals."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import bmesh
import bpy


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export_clean_normals_v219():
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(values)
    output = args.output_dir.resolve()
    if output.exists() and any(output.iterdir()):
        raise RuntimeError(f"refusing to overwrite immutable v219 package: {output}")
    source_blend = Path(bpy.data.filepath).resolve()
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not source_blend.is_file() or len(meshes) != 1:
        raise RuntimeError("saved normalized v178 scene with one mesh required")
    source = meshes[0]
    before_custom_normals = bool(source.data.has_custom_normals)

    target = source.copy()
    target.data = source.data.copy()
    target.name = "Gahyeon_KeenTools_CleanNormals_v219"
    bpy.context.scene.collection.objects.link(target)
    bm = bmesh.new()
    bm.from_mesh(target.data)
    remaining = {face for face in bm.faces if face.material_index == 0}
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
    sizes = [len(component) for component in components]
    if sizes[:3] != [45140, 1236, 1236]:
        bm.free()
        raise RuntimeError(f"v178 component contract differs: {sizes}")
    retained = components[0]
    bmesh.ops.delete(bm, geom=[face for face in bm.faces if face not in retained], context="FACES")
    loose = [vertex for vertex in bm.verts if not vertex.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(target.data)
    bm.free()

    bpy.ops.object.select_all(action="DESELECT")
    target.hide_set(False)
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.customdata_custom_splitnormals_clear()
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    for polygon in target.data.polygons:
        polygon.use_smooth = True
    target.data.materials.clear()
    target.data.materials.append(source.data.materials[0])
    target.data.update(calc_edges=True)
    bpy.context.view_layer.update()

    if target.data.has_custom_normals:
        raise RuntimeError("v219 custom split normals were not removed")
    if (len(target.data.vertices), len(target.data.polygons)) != (22808, 45140):
        raise RuntimeError("v219 retained topology differs")
    smooth_count = sum(1 for polygon in target.data.polygons if polygon.use_smooth)
    if smooth_count != 45140:
        raise RuntimeError(f"v219 smooth polygon contract failed: {smooth_count}")

    output.mkdir(parents=True, exist_ok=True)
    source.hide_set(True)
    fbx = output / "gahyeon-keentools-clean-normals-v219.fbx"
    bpy.ops.export_scene.fbx(
        filepath=str(fbx), use_selection=True, bake_anim=False, add_leaf_bones=False,
        mesh_smooth_type="OFF", axis_forward="Y", axis_up="Z",
        bake_space_transform=False, path_mode="COPY", embed_textures=False,
    )
    manifest = {
        "schemaVersion": 1,
        "iteration": "v219",
        "state": "clean-normal-head-target-awaiting-unreal-portrait-qa",
        "hypothesis": "Corrupted imported custom split normals caused the unusable UE face-tracker portrait.",
        "source": {"path": str(source_blend), "sha256": digest(source_blend)},
        "exporterSha256": digest(Path(__file__).resolve()),
        "normalContract": {
            "sourceHadCustomNormals": before_custom_normals,
            "targetHasCustomNormals": bool(target.data.has_custom_normals),
            "recalculatedFaceNormals": True,
            "smoothPolygons": smooth_count,
        },
        "topology": {
            "vertices": len(target.data.vertices),
            "polygons": len(target.data.polygons),
            "retainedConnectedComponentFaces": len(retained),
            "dimensionsCm": [round(float(value), 6) for value in target.dimensions],
        },
        "files": [{"uri": fbx.name, "bytes": fbx.stat().st_size, "sha256": digest(fbx)}],
        "claims": {"identityApproved": False, "metaHumanConformed": False, "productionReady": False},
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == "__main__":
    export_clean_normals_v219()
