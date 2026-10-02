"""Reconstruct Stella/Lily material channels while preserving all modular meshes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy


MATERIAL_CHANNELS = {
    "MI_CH_HR_NPC_Lily": {
        "base": "CH_NPC_Lilly_01_Hair_A0001.png",
        "normal": "CH_NPC_Lilly_01_Hair_Normal0001.png",
        "roughness": 0.42,
    },
    "MI_CH_NPC_01_DX_Lower": {
        "base": "CH_NPC_01_DX_Lower_A0001.png",
        "normal": "CH_NPC_01_DX_Lower_N0001.png",
        "roughness": 0.58,
    },
    "MI_CH_NPC_01_DX_Skin": {
        "base": "CH_NPC_01_DX_Skin_A0001.png",
        "normal": "CH_NPC_01_DX_Skin_N0001.png",
        "roughness": 0.46,
    },
    "MI_CH_NPC_01_DX_Upper": {
        "base": "CH_NPC_01_DX_Upper_A0001.png",
        "normal": "CH_NPC_01_DX_Upper_N0001.png",
        "roughness": 0.55,
    },
    "MI_NPC_Lilly_Head": {
        "base": "CH_NPC_Lilly_01_Head_A0001.png",
        "normal": "CH_NPC_Lilly_01_Head_N0001.png",
        "roughness": 0.44,
    },
    "MI_CH_NPC_Lilly_Eyes": {
        "base": "EVE_Std_Eye_R_DiffuseRL.png",
        "normal": "T_EYE_NORMALS.png",
        "roughness": 0.18,
    },
    "MI_Teeth": {
        "base": "Tex_P_EVE_Teeth_A0001.png",
        "normal": "Tex_P_EVE_Teeth_N0001.png",
        "roughness": 0.28,
    },
}

FALLBACK_COLORS = {
    "MA_TeethOcculusion_Inst1": (0.015, 0.008, 0.008, 1.0),
    "MI_CH_NPC_Lilly_Eyebrow": (0.055, 0.028, 0.018, 1.0),
    "MI_CH_NPC_Lilly_Eyeshadow": (0.12, 0.05, 0.065, 1.0),
    "MI_CH_NPC_Lilly_Eyeshadow2": (0.12, 0.05, 0.065, 1.0),
    "MI_Tearline_Lily": (0.75, 0.88, 0.95, 1.0),
    "NewMaterial": (0.02, 0.02, 0.025, 1.0),
}

BROKEN_SPECIAL_SHADER_MESHES = {
    "MI_CH_NPC_Lilly_Eyeshadow",
    "MI_CH_NPC_Lilly_Eyeshadow2",
    "MI_Tearline_Lily",
    "NewMaterial",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def image_node(nodes, texture_path: Path, name: str, non_color: bool = False):
    node = nodes.new("ShaderNodeTexImage")
    node.name = name
    node.label = name
    node.image = bpy.data.images.load(str(texture_path), check_existing=True)
    node.interpolation = "Linear"
    if non_color:
        node.image.colorspace_settings.name = "Non-Color"
    return node


def rebuild_stella_material(material: bpy.types.Material, textures: Path) -> dict[str, object]:
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])

    specification = MATERIAL_CHANNELS.get(material.name)
    channels = []
    if specification:
        base_path = textures / str(specification["base"])
        normal_path = textures / str(specification["normal"])
        if not base_path.is_file() or not normal_path.is_file():
            raise FileNotFoundError(f"missing channel for {material.name}: {base_path}, {normal_path}")
        base = image_node(nodes, base_path, "BaseColor")
        normal_texture = image_node(nodes, normal_path, "Normal", non_color=True)
        normal_map = nodes.new("ShaderNodeNormalMap")
        links.new(base.outputs["Color"], shader.inputs["Base Color"])
        links.new(normal_texture.outputs["Color"], normal_map.inputs["Color"])
        links.new(normal_map.outputs["Normal"], shader.inputs["Normal"])
        shader.inputs["Roughness"].default_value = float(specification["roughness"])
        nodes.active = base
        channels = [
            {"role": "baseColor", "file": str(base_path), "sha256": sha256(base_path)},
            {"role": "normal", "file": str(normal_path), "sha256": sha256(normal_path)},
        ]
    else:
        color = FALLBACK_COLORS.get(material.name, (0.18, 0.18, 0.2, 1.0))
        shader.inputs["Base Color"].default_value = color
        shader.inputs["Roughness"].default_value = 0.55
    return {"material": material.name, "channels": channels}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--textures", required=True, type=Path)
    parser.add_argument("--output-fbx", required=True, type=Path)
    parser.add_argument("--output-blend", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--iteration", required=True)
    parser.add_argument("--disable-broken-eye-shells", action="store_true")
    arguments = parser.parse_args()
    for name in ("source", "textures", "output_fbx", "output_blend", "report"):
        setattr(arguments, name, getattr(arguments, name).resolve())

    for output in (arguments.output_fbx, arguments.output_blend, arguments.report):
        if output.exists():
            raise FileExistsError(f"refusing to overwrite immutable output: {output}")
    if not arguments.source.is_file():
        raise FileNotFoundError(arguments.source)

    if bpy.data.filepath != str(arguments.source):
        bpy.ops.wm.open_mainfile(filepath=str(arguments.source))
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH" and len(obj.data.polygons) > 0]
    if len(armatures) != 1 or len(meshes) != 13:
        raise RuntimeError(f"expected one rig and 13 modular meshes, got {len(armatures)}/{len(meshes)}")

    rebuilt = [rebuild_stella_material(material, arguments.textures) for material in bpy.data.materials]
    channel_materials = {entry["material"] for entry in rebuilt if entry["channels"]}
    missing = sorted(set(MATERIAL_CHANNELS) - channel_materials)
    if missing:
        raise RuntimeError(f"required Stella materials missing: {missing}")

    preview_excluded = []
    if arguments.disable_broken_eye_shells:
        for obj in meshes:
            if obj.name in BROKEN_SPECIAL_SHADER_MESHES:
                obj.hide_render = True
                preview_excluded.append(obj.name)

    output_directories = {
        arguments.output_fbx.parent,
        arguments.output_blend.parent,
        arguments.report.parent,
    }
    for output_directory in output_directories:
        output_directory.mkdir(parents=True, exist_ok=False)
    bpy.ops.wm.save_as_mainfile(filepath=str(arguments.output_blend), check_existing=False)
    armatures[0].hide_set(False)
    armatures[0].hide_viewport = False
    export_meshes = [obj for obj in meshes if obj.name not in preview_excluded]
    bpy.ops.object.select_all(action="DESELECT")
    for obj in [armatures[0], *export_meshes]:
        obj.hide_set(False)
        obj.hide_viewport = False
        obj.hide_render = False
        obj.select_set(True)
    bpy.context.view_layer.objects.active = armatures[0]
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
        "status": "authored-draft-stella-material-channels-restored",
        "source": {"file": str(arguments.source), "sha256": sha256(arguments.source)},
        "output": {
            "fbx": str(arguments.output_fbx),
            "fbxSha256": sha256(arguments.output_fbx),
            "blend": str(arguments.output_blend),
            "blendSha256": sha256(arguments.output_blend),
        },
        "meshCount": len(meshes),
        "previewExportMeshCount": len(export_meshes),
        "previewExcludedMeshes": sorted(preview_excluded),
        "boneCount": len(armatures[0].data.bones),
        "modularMeshesPreserved": True,
        "materials": rebuilt,
        "hypothesis": "Restoring Stella's named base-color and normal channels makes the original 13-piece character visually identifiable without changing topology, rig, or modularity.",
        "visualValidationPending": True,
        "humanApproved": False,
        "releaseEligible": False,
    }
    arguments.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("STELLA_MATERIAL_REBUILD=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    if "--" not in sys.argv:
        raise RuntimeError("pass script arguments after --")
    sys.argv = [sys.argv[0], *sys.argv[sys.argv.index("--") + 1 :]]
    main()
