#!/usr/bin/env python3
"""Import a real base mesh into a sealed G1 Blender authoring scene."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

try:
    import bpy
except ImportError as error:  # pragma: no cover - Blender runtime only
    raise SystemExit("Run this script with Blender's Python runtime") from error


MAX_SOURCE_BYTES = 2 * 1024 * 1024 * 1024
FORMATS = {".fbx": "fbx", ".glb": "glb", ".gltf": "gltf"}


def parse_args() -> argparse.Namespace:
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(values)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def move_to_collection(obj, collection) -> None:
    for current in tuple(obj.users_collection):
        current.objects.unlink(obj)
    collection.objects.link(obj)


def main() -> None:
    args = parse_args()
    source = args.base.resolve()
    output = args.output.resolve()
    if not source.is_file() or source.is_symlink():
        raise SystemExit(f"Base mesh is missing or unsafe: {source}")
    if source.stat().st_size <= 0 or source.stat().st_size > MAX_SOURCE_BYTES:
        raise SystemExit("Base mesh size is outside the accepted boundary")
    source_format = FORMATS.get(source.suffix.lower())
    if source_format is None:
        raise SystemExit("G1 base mesh must be FBX, GLB, or glTF")
    if output.exists():
        raise SystemExit(f"Refusing to overwrite existing Blender file: {output}")
    required = {"G1_MODEL_BODY", "G1_RIG", "G1_GUIDES_NON_AUTHORITATIVE"}
    if not required.issubset({collection.name for collection in bpy.data.collections}):
        raise SystemExit("Open the sealed G1 authoring bootstrap before importing a base mesh")
    if bpy.context.scene.get("gahyeon_character_id") != "gahyeon":
        raise SystemExit("Current Blender scene is not the Gahyeon G1 authoring scene")

    previous = set(bpy.data.objects)
    if source_format == "fbx":
        bpy.ops.import_scene.fbx(filepath=str(source), automatic_bone_orientation=False)
    else:
        bpy.ops.import_scene.gltf(filepath=str(source))
    imported = [obj for obj in bpy.data.objects if obj not in previous]
    meshes = [obj for obj in imported if obj.type == "MESH"]
    if not meshes:
        raise SystemExit("Imported base contains no mesh objects")

    source_digest = sha256(source)
    for obj in imported:
        target = (bpy.data.collections["G1_RIG"] if obj.type == "ARMATURE"
                  else bpy.data.collections["G1_MODEL_BODY"])
        move_to_collection(obj, target)
        obj["gahyeon_source_sha256"] = source_digest
        obj["gahyeon_source_format"] = source_format
        obj["gahyeon_import_role"] = "unreviewed-base"
        obj["gahyeon_identity_approved"] = False

    scene = bpy.context.scene
    scene["gahyeon_base_source_sha256"] = source_digest
    scene["gahyeon_base_source_bytes"] = source.stat().st_size
    scene["gahyeon_base_source_format"] = source_format
    scene["gahyeon_base_review_status"] = "unreviewed"
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output), check_existing=False)
    print(json.dumps({
        "saved": str(output),
        "sourceSha256": source_digest,
        "sourceFormat": source_format,
        "importedObjects": len(imported),
        "meshObjects": len(meshes),
        "armatures": sum(obj.type == "ARMATURE" for obj in imported),
        "reviewStatus": "unreviewed",
    }))


if __name__ == "__main__":
    main()
