"""Export a neutral v79 mesh package for Unreal Mesh-to-MetaHuman Identity Solve.

Run inside Blender. This is a solve input, never a MetaHuman/DNA deliverable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import bmesh
import bpy


SOURCE_OBJECTS = (
    "Gahyeon_G1_BodyFace_CC0",
    "Gahyeon_G1_Eyes_high-poly",
)


def parse_args() -> argparse.Namespace:
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-revision", default="g1-mpfb-v79")
    parser.add_argument("--topology-audit", type=Path, required=True)
    return parser.parse_args(values)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def duplicate_source_mesh(name: str):
    source = bpy.data.objects.get(name)
    if source is None or source.type != "MESH":
        raise SystemExit(f"missing required MetaHuman solve source mesh: {name}")
    result = source.copy()
    result.name = f"M2MH_{name}"
    result.data = source.data.copy()
    bpy.context.scene.collection.objects.link(result)
    # MPFB stores helper geometry in the body mesh and hides it with MASK modifiers.
    # Preserve and apply only those masks; solve input must remain neutral and low-poly.
    for modifier in list(result.modifiers):
        if modifier.type != "MASK":
            result.modifiers.remove(modifier)
    if result.modifiers:
        bpy.ops.object.select_all(action="DESELECT")
        result.select_set(True)
        bpy.context.view_layer.objects.active = result
        bpy.ops.object.convert(target="MESH")
    if name == "Gahyeon_G1_BodyFace_CC0":
        keep_head_component(result)
    return result


def keep_head_component(obj) -> None:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
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
    head = max(components, key=lambda vertices: max(vertex.co.z for vertex in vertices))
    if len(head) < 1_000:
        raise SystemExit("highest connected surface is too small to be the head")
    bmesh.ops.delete(
        bm, geom=[vertex for vertex in bm.verts if vertex not in head], context="VERTS"
    )
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def save_packed_image(name: str, destination: Path) -> None:
    image = bpy.data.images.get(name)
    if image is None or image.packed_file is None:
        raise SystemExit(f"required packed solve texture is missing: {name}")
    original_raw = image.filepath_raw
    original_format = image.file_format
    try:
        image.filepath_raw = str(destination)
        image.file_format = "PNG"
        image.save()
    finally:
        image.filepath_raw = original_raw
        image.file_format = original_format


def add_texture_to_mtl(mtl_path: Path, material_names: list[str], texture: str) -> None:
    lines = mtl_path.read_text(encoding="utf-8").splitlines()
    updated = []
    active = None
    inserted = set()
    for line in lines:
        if line.startswith("newmtl "):
            if active in material_names and active not in inserted:
                updated.append(f"map_Kd {texture}")
                inserted.add(active)
            active = line.removeprefix("newmtl ")
        if active in material_names and line.startswith(("map_Kd ", "map_d ")):
            continue
        updated.append(line)
    if active in material_names and active not in inserted:
        updated.append(f"map_Kd {texture}")
        inserted.add(active)
    missing = sorted(set(material_names) - inserted)
    if missing:
        raise SystemExit(f"OBJ material export omitted required materials: {missing}")
    mtl_path.write_text("\n".join(updated) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise SystemExit(f"refusing to overwrite non-empty output directory: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    topology_audit = json.loads(args.topology_audit.resolve().read_text(encoding="utf-8"))
    totals = topology_audit.get("totals", {})
    if (totals.get("connectedComponents") != 5
            or totals.get("boundaryEdges") != 122
            or totals.get("boundaryLoops") != 5):
        raise SystemExit("topology audit does not match the reviewed head/eyes open-boundary policy")

    bpy.ops.object.select_all(action="DESELECT")
    exports = [duplicate_source_mesh(name) for name in SOURCE_OBJECTS]
    for item in exports:
        item.select_set(True)
    bpy.context.view_layer.objects.active = exports[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.join()
    solve_mesh = bpy.context.view_layer.objects.active
    solve_mesh.name = "Gahyeon_MetaHuman_IdentitySolve_v79"

    if len(solve_mesh.data.vertices) < 4_000 or len(solve_mesh.data.polygons) < 4_000:
        raise SystemExit(
            "combined solve mesh unexpectedly lost face or eye geometry: "
            f"{len(solve_mesh.data.vertices)} vertices/{len(solve_mesh.data.polygons)} polygons"
        )
    material_names = [material.name for material in solve_mesh.data.materials if material]
    if not any("body" in name.lower() for name in material_names):
        raise SystemExit("solve mesh is missing skin material separation")
    if not any("high-poly" in name.lower() for name in material_names):
        raise SystemExit("solve mesh is missing sclera material separation")

    obj_path = output_dir / "gahyeon-metahuman-identity-v79.obj"
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

    skin_texture = "gahyeon-v79-skin-albedo.png"
    eye_texture = "gahyeon-v79-eye-albedo.png"
    save_packed_image("young_lightskinned_female_diffuse3.png", output_dir / skin_texture)
    save_packed_image("brown_eye.png", output_dir / eye_texture)
    mtl_path = obj_path.with_suffix(".mtl")
    skin_materials = [
        name for name in material_names
        if name.startswith("Gahyeon_G1_BodyFace_CC0.") and "high-poly" not in name
    ]
    add_texture_to_mtl(mtl_path, skin_materials, skin_texture)
    add_texture_to_mtl(
        mtl_path, ["Gahyeon_G1_BodyFace_CC0.high-poly"], eye_texture
    )

    files = sorted(path for path in output_dir.iterdir() if path.is_file())
    manifest = {
        "schemaVersion": 1,
        "characterId": "gahyeon",
        "purpose": "unreal-mesh-to-metahuman-identity-solve-input",
        "claim": "neutral-static-mesh-input-not-metahuman-not-dna",
        "scope": "head-neck-and-eyes-only",
        "sourceRevision": args.source_revision,
        "sourceBlend": bpy.data.filepath,
        "sourceBlendSha256": digest(Path(bpy.data.filepath)),
        "exporterSha256": digest(Path(__file__).resolve()),
        "mesh": {
            "object": solve_mesh.name,
            "vertices": len(solve_mesh.data.vertices),
            "polygons": len(solve_mesh.data.polygons),
            "uvLayers": [item.name for item in solve_mesh.data.uv_layers],
            "materials": material_names,
            "sourceObjects": list(SOURCE_OBJECTS),
        },
        "unrealImport": {
            "combineMeshes": True,
            "neutralPose": True,
            "eyesOpen": True,
            "identityWorkflow": "MetaHuman Identity / Components From Mesh",
        },
        "topologyPolicy": {
            "auditSha256": digest(args.topology_audit.resolve()),
            "connectedComponents": 5,
            "boundaryEdges": 122,
            "boundaryLoops": 5,
            "openBoundaryPolicy": "one reviewed head-neck cut plus four reviewed base-eyeball shell loops; semantic iris render helpers excluded"
        },
        "files": [
            {"uri": path.name, "bytes": path.stat().st_size, "sha256": digest(path)}
            for path in files
        ],
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
