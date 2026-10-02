"""Rebuild Ururu's broken FBX texture bindings and export an immutable UE package."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import bpy


TEXTURE_BY_MATERIAL = {
    "Ururu_Skin": "ururu_skin.jpg",
    "Ururu_Underwear": "ururu_underwear.jpg",
    "Ururu_Hair": "ururu_hair.jpg",
    "Ururu_Cloth1": "ururu_cloth1.jpg",
    "tops": "tops.jpg",
    "tops2": "tops2.jpg",
    "skirt": "skirt.jpg",
    "skirt1": "skirt1.jpg",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.armatures, bpy.data.meshes, bpy.data.materials, bpy.data.images):
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)


def rebuild_material(material: bpy.types.Material, texture_path: Path) -> None:
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    texture = nodes.new("ShaderNodeTexImage")
    texture.image = bpy.data.images.load(str(texture_path), check_existing=True)
    texture.interpolation = "Linear"
    material.node_tree.links.new(texture.outputs["Color"], shader.inputs["Base Color"])
    material.node_tree.links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    shader.inputs["Roughness"].default_value = 0.48 if material.name == "Ururu_Skin" else 0.62
    if material.name == "Ururu_Skin":
        shader.inputs["IOR"].default_value = 1.4


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--textures", required=True, type=Path)
    parser.add_argument("--output-fbx", required=True, type=Path)
    parser.add_argument("--output-blend", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--iteration", required=True)
    arguments = parser.parse_args()

    arguments.source = arguments.source.resolve()
    arguments.textures = arguments.textures.resolve()
    arguments.output_fbx = arguments.output_fbx.resolve()
    arguments.output_blend = arguments.output_blend.resolve()
    arguments.report = arguments.report.resolve()

    for output in (arguments.output_fbx, arguments.output_blend, arguments.report):
        if output.exists():
            raise FileExistsError(f"refusing to overwrite immutable v544 output: {output}")
    if not arguments.source.is_file():
        raise FileNotFoundError(arguments.source)

    reset_scene()
    bpy.ops.import_scene.fbx(filepath=str(arguments.source), use_anim=False)
    rebuilt = []
    unresolved = []
    for material in bpy.data.materials:
        texture_name = TEXTURE_BY_MATERIAL.get(material.name)
        if texture_name is None:
            unresolved.append(material.name)
            continue
        texture_path = arguments.textures / texture_name
        if not texture_path.is_file():
            raise FileNotFoundError(texture_path)
        rebuild_material(material, texture_path)
        rebuilt.append({
            "material": material.name,
            "texture": str(texture_path),
            "textureSha256": sha256(texture_path),
        })

    if len(rebuilt) != len(TEXTURE_BY_MATERIAL):
        rebuilt_names = {item["material"] for item in rebuilt}
        missing = sorted(set(TEXTURE_BY_MATERIAL) - rebuilt_names)
        raise RuntimeError(f"not all required Ururu materials were present: {missing}")

    output_directories = {
        arguments.output_fbx.parent,
        arguments.output_blend.parent,
        arguments.report.parent,
    }
    for output_directory in output_directories:
        output_directory.mkdir(parents=True, exist_ok=False)
    bpy.ops.wm.save_as_mainfile(filepath=str(arguments.output_blend), check_existing=False)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.fbx(
        filepath=str(arguments.output_fbx),
        use_selection=True,
        object_types={"ARMATURE", "MESH"},
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_ALL",
        add_leaf_bones=False,
        bake_anim=False,
        path_mode="COPY",
        embed_textures=True,
    )
    report = {
        "schemaVersion": 1,
        "iteration": arguments.iteration,
        "status": "authored-draft-texture-bindings-restored",
        "source": {"file": str(arguments.source), "sha256": sha256(arguments.source)},
        "output": {
            "fbx": str(arguments.output_fbx),
            "fbxSha256": sha256(arguments.output_fbx),
            "blend": str(arguments.output_blend),
            "blendSha256": sha256(arguments.output_blend),
        },
        "rebuiltMaterials": rebuilt,
        "unresolvedMaterials": sorted(unresolved),
        "hypothesis": "Restoring each named material's original color texture makes the normalized Ururu candidate visually identifiable in Unreal without changing geometry or rigging.",
        "visualValidationPending": True,
        "humanApproved": False,
        "releaseEligible": False,
    }
    arguments.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("URURU_MATERIAL_REBUILD=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    import sys

    if "--" not in sys.argv:
        raise RuntimeError("pass script arguments after --")
    sys.argv = [sys.argv[0], *sys.argv[sys.argv.index("--") + 1 :]]
    main()
