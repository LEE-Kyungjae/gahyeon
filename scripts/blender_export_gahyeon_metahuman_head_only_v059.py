"""Export a single-surface head/neck MetaHuman Identity solve input for v059."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import bmesh
import bpy


def export_head_only_v059() -> int:
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-revision", default="g1-mpfb-v79-head-only-v059")
    args = parser.parse_args(values)
    output_dir = args.output_dir.resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise SystemExit(f"refusing to overwrite non-empty output directory: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    def digest(path: Path) -> str:
        value = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                value.update(chunk)
        return value.hexdigest()

    source = bpy.data.objects.get("Gahyeon_G1_BodyFace_CC0")
    if source is None or source.type != "MESH":
        raise SystemExit("missing Gahyeon_G1_BodyFace_CC0 source mesh")
    head = source.copy()
    head.name = "Gahyeon_MetaHuman_HeadOnly_v059"
    head.data = source.data.copy()
    bpy.context.scene.collection.objects.link(head)
    for modifier in list(head.modifiers):
        if modifier.type != "MASK":
            head.modifiers.remove(modifier)
    if head.modifiers:
        bpy.ops.object.select_all(action="DESELECT")
        head.select_set(True)
        bpy.context.view_layer.objects.active = head
        bpy.ops.object.convert(target="MESH")

    bm = bmesh.new()
    bm.from_mesh(head.data)
    remaining = set(bm.verts)
    components = []
    while remaining:
        seed = remaining.pop()
        component = {seed}
        frontier = [seed]
        while frontier:
            vertex = frontier.pop()
            for edge in vertex.link_edges:
                neighbour = edge.other_vert(vertex)
                if neighbour in remaining:
                    remaining.remove(neighbour)
                    component.add(neighbour)
                    frontier.append(neighbour)
        components.append(component)
    if not components:
        raise SystemExit("masked body produced no connected surface")
    selected = max(components, key=lambda vertices: max(vertex.co.z for vertex in vertices))
    if len(selected) < 4_000:
        raise SystemExit(f"head surface is unexpectedly small: {len(selected)} vertices")
    bmesh.ops.delete(bm, geom=[vertex for vertex in bm.verts if vertex not in selected], context="VERTS")
    bm.to_mesh(head.data)
    bm.free()
    head.data.update()

    bpy.ops.object.select_all(action="DESELECT")
    head.select_set(True)
    bpy.context.view_layer.objects.active = head
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    material_names = [material.name for material in head.data.materials if material]
    if not any("body" in name.lower() for name in material_names):
        raise SystemExit("head-only mesh lost its skin material")

    obj_path = output_dir / "gahyeon-metahuman-head-only-v059.obj"
    bpy.ops.wm.obj_export(
        filepath=str(obj_path),
        export_selected_objects=True,
        export_materials=True,
        export_uv=True,
        export_normals=True,
        export_triangulated_mesh=False,
        path_mode="COPY",
        forward_axis="NEGATIVE_Z",
        up_axis="Y",
    )
    skin_name = "gahyeon-v059-skin-albedo.png"
    skin = bpy.data.images.get("young_lightskinned_female_diffuse3.png")
    if skin is None or skin.packed_file is None:
        raise SystemExit("packed skin albedo is unavailable")
    original_path, original_format = skin.filepath_raw, skin.file_format
    try:
        skin.filepath_raw = str(output_dir / skin_name)
        skin.file_format = "PNG"
        skin.save()
    finally:
        skin.filepath_raw, skin.file_format = original_path, original_format

    mtl_path = obj_path.with_suffix(".mtl")
    lines = mtl_path.read_text(encoding="utf-8").splitlines()
    updated, active, inserted = [], None, set()
    skin_materials = {name for name in material_names if name.startswith("Gahyeon_G1_BodyFace_CC0.")}
    for line in lines:
        if line.startswith("newmtl "):
            if active in skin_materials and active not in inserted:
                updated.append(f"map_Kd {skin_name}")
                inserted.add(active)
            active = line.removeprefix("newmtl ")
        if active in skin_materials and line.startswith(("map_Kd ", "map_d ")):
            continue
        updated.append(line)
    if active in skin_materials and active not in inserted:
        updated.append(f"map_Kd {skin_name}")
        inserted.add(active)
    if inserted != skin_materials:
        raise SystemExit(f"OBJ omitted skin materials: {sorted(skin_materials - inserted)}")
    mtl_path.write_text("\n".join(updated) + "\n", encoding="utf-8")

    files = sorted(path for path in output_dir.iterdir() if path.is_file())
    manifest = {
        "schemaVersion": 1,
        "characterId": "gahyeon",
        "iteration": "v059",
        "purpose": "unreal-mesh-to-metahuman-identity-solve-input",
        "claim": "neutral-head-only-static-mesh-input-not-metahuman-not-dna",
        "scope": "single-connected-head-neck-skin-surface-no-eyes-no-teeth",
        "sourceRevision": args.source_revision,
        "sourceBlend": bpy.data.filepath,
        "sourceBlendSha256": digest(Path(bpy.data.filepath)),
        "exporterSha256": digest(Path(__file__).resolve()),
        "mesh": {
            "object": head.name,
            "vertices": len(head.data.vertices),
            "polygons": len(head.data.polygons),
            "uvLayers": [layer.name for layer in head.data.uv_layers],
            "materials": material_names,
            "sourceObjects": [source.name],
        },
        "unrealImport": {
            "combineMeshes": True,
            "neutralPose": True,
            "eyesExcludedFromTracking": True,
            "useMetaHumanDefaultEyes": True,
            "useMetaHumanDefaultTeeth": True,
            "identityWorkflow": "MetaHuman Identity / Components From Mesh",
        },
        "status": "draft",
        "automaticApproval": False,
        "productionReady": False,
        "aaaQualityClaim": False,
        "files": [
            {"uri": path.name, "bytes": path.stat().st_size, "sha256": digest(path)}
            for path in files
        ],
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(export_head_only_v059())
