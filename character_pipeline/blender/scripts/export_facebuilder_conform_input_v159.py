"""Seal a reviewed FaceBuilder auto-fit as a UE 5.8 Custom Mesh input.

Run inside Blender with the immutable v158 workspace open. The export remains
an unapproved reconstruction candidate; MetaHuman conform and visual identity
review are later gates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import bmesh
import bpy


def parse_args_v159() -> argparse.Namespace:
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-cameras", type=int, default=4)
    return parser.parse_args(values)


def digest_v159(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def audit_facebuilder_head_v159(obj: bpy.types.Object) -> dict:
    if obj.type != "MESH":
        raise RuntimeError(f"FaceBuilder head is not a mesh: {obj.type}")
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    boundary_edges = sum(1 for edge in bm.edges if len(edge.link_faces) == 1)
    non_manifold_over_two = sum(1 for edge in bm.edges if len(edge.link_faces) > 2)
    loose_edges = sum(1 for edge in bm.edges if len(edge.link_faces) == 0)
    bm.free()
    if len(mesh.vertices) < 1_000 or len(mesh.polygons) < 1_000:
        raise RuntimeError("FaceBuilder head unexpectedly lacks production shape density")
    if non_manifold_over_two or loose_edges:
        raise RuntimeError(
            f"unsafe head topology: overTwo={non_manifold_over_two}, loose={loose_edges}"
        )
    return {
        "object": obj.name,
        "vertices": len(mesh.vertices),
        "polygons": len(mesh.polygons),
        "boundaryEdges": boundary_edges,
        "nonManifoldEdgesOverTwoFaces": non_manifold_over_two,
        "looseEdges": loose_edges,
        "uvLayers": [layer.name for layer in mesh.uv_layers],
        "materials": [slot.name for slot in mesh.materials if slot],
    }


def export_facebuilder_conform_input_v159() -> dict:
    args = parse_args_v159()
    output_dir = args.output_dir.resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError(f"refusing to overwrite non-empty output: {output_dir}")
    if not bpy.data.filepath:
        raise RuntimeError("FaceBuilder workspace must be saved before export")

    from keentools.addon_config import fb_settings
    from keentools.facebuilder.fbloader import FBLoader

    settings = fb_settings()
    heads = list(settings.heads)
    if len(heads) != 1 or heads[0].headobj is None:
        raise RuntimeError(f"expected exactly one FaceBuilder head, found {len(heads)}")
    head = heads[0]
    if len(head.cameras) != args.expected_cameras:
        raise RuntimeError(
            f"expected {args.expected_cameras} canonical cameras, found {len(head.cameras)}"
        )
    if not FBLoader.load_model(0):
        raise RuntimeError("FaceBuilder serialized model could not be loaded")
    builder = FBLoader.get_builder()
    cameras = []
    for index, camera in enumerate(head.cameras):
        keyframe = camera.get_keyframe()
        pin_count = builder.pins_count(keyframe)
        if pin_count < 4:
            raise RuntimeError(f"camera {index} has insufficient pins: {pin_count}")
        cameras.append({
            "cameraIndex": index,
            "keyframe": keyframe,
            "pinCount": pin_count,
            "focalLengthMm": camera.focal,
            "imagePath": camera.get_abspath(),
        })

    topology = audit_facebuilder_head_v159(head.headobj)
    output_dir.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    head.headobj.hide_set(False)
    head.headobj.select_set(True)
    bpy.context.view_layer.objects.active = head.headobj

    obj_path = output_dir / "gahyeon-facebuilder-v159.obj"
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
    fbx_path = output_dir / "gahyeon-facebuilder-v159.fbx"
    bpy.ops.export_scene.fbx(
        filepath=str(fbx_path),
        use_selection=True,
        bake_anim=False,
        add_leaf_bones=False,
        mesh_smooth_type="FACE",
        axis_forward="Y",
        axis_up="Z",
        bake_space_transform=False,
        path_mode="COPY",
        embed_textures=True,
    )
    if not obj_path.is_file() or not fbx_path.is_file():
        raise RuntimeError("FaceBuilder mesh export did not produce both OBJ and FBX")

    workspace = Path(bpy.data.filepath).resolve()
    payload_files = sorted(path for path in output_dir.iterdir() if path.is_file())
    manifest = {
        "schemaVersion": 1,
        "iteration": "v159",
        "characterId": "gahyeon",
        "state": "reconstruction-export-awaiting-metahuman-conform-and-identity-review",
        "purpose": "ue58-metahuman-from-custom-mesh-input",
        "sourceWorkspace": {"path": str(workspace), "sha256": digest_v159(workspace)},
        "exporterSha256": digest_v159(Path(__file__).resolve()),
        "topology": topology,
        "canonicalCameras": cameras,
        "files": [
            {"uri": path.name, "bytes": path.stat().st_size, "sha256": digest_v159(path)}
            for path in payload_files
        ],
        "claims": {
            "coherentMultiViewReconstruction": True,
            "identityApproved": False,
            "metaHumanConformed": False,
            "productionReady": False,
        },
        "requiredNextActions": [
            "inspect the four camera pin overlays against canonical identity",
            "import FBX into UE 5.8 as Custom Mesh target",
            "track the exact neutral target camera and conform MetaHuman topology",
            "render fixed front, 45-degree and profile identity comparisons",
        ],
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False))
    return manifest


if __name__ == "__main__":
    export_facebuilder_conform_input_v159()
