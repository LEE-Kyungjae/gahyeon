"""Extract donor body, separated clothing, and deformation rig into immutable outputs."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-blend", required=True, type=Path)
    parser.add_argument("--output-fbx", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    return parser.parse_args(argv)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


args = parse_args()
source_scene = Path(bpy.data.filepath).resolve()
if not source_scene.is_file():
    raise RuntimeError(f"donor source scene is unavailable: {source_scene}")
source_scene_sha256 = sha256(source_scene)
for output in (args.output_blend, args.output_fbx, args.report):
    if output.exists():
        raise RuntimeError(f"refusing to overwrite donor extraction: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

required_names = ("Body", "top_cloth", "bottome", "blender file_Rigify")
required = {name: bpy.data.objects.get(name) for name in required_names}
missing = [name for name, obj in required.items() if obj is None]
if missing:
    raise RuntimeError(f"donor scene is missing required objects: {missing}")
body = required["Body"]
top = required["top_cloth"]
bottom = required["bottome"]
rig = required["blender file_Rigify"]
if any(obj.type != "MESH" for obj in (body, top, bottom)) or rig.type != "ARMATURE":
    raise RuntimeError("donor extraction object types differ")
for garment in (top, bottom):
    armatures = [modifier for modifier in garment.modifiers if modifier.type == "ARMATURE"]
    if len(armatures) != 1 or armatures[0].object != rig:
        raise RuntimeError(f"{garment.name} lacks the expected Rigify armature")
    if not garment.vertex_groups:
        raise RuntimeError(f"{garment.name} has no skin weights")

# Work only in memory; the purchased source .blend remains unchanged on disk.
keep = set(required.values())
for obj in list(bpy.data.objects):
    if obj not in keep:
        bpy.data.objects.remove(obj, do_unlink=True)
for obj in bpy.data.objects:
    obj.hide_set(False)
    obj.hide_render = False
    obj.select_set(False)

bpy.ops.wm.save_as_mainfile(filepath=str(args.output_blend.resolve()))
for obj in (top, bottom, rig):
    obj.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.export_scene.fbx(
    filepath=str(args.output_fbx.resolve()),
    use_selection=True,
    object_types={"MESH", "ARMATURE"},
    use_mesh_modifiers=True,
    add_leaf_bones=False,
    bake_anim=False,
    path_mode="COPY",
    embed_textures=True,
)

report = {
    "schemaVersion": 1,
    "state": "extracted-donor-candidate",
    "source": {
        "file": str(source_scene),
        "sha256": source_scene_sha256,
    },
    "identityAuthority": False,
    "productionReady": False,
    "objects": {
        "bodyReference": {
            "name": body.name,
            "vertices": len(body.data.vertices),
            "shapeKeys": len(body.data.shape_keys.key_blocks) if body.data.shape_keys else 0,
        },
        "top": {
            "name": top.name,
            "vertices": len(top.data.vertices),
            "polygons": len(top.data.polygons),
            "vertexGroups": len(top.vertex_groups),
            "materials": [slot.material.name if slot.material else None for slot in top.material_slots],
        },
        "bottom": {
            "name": bottom.name,
            "vertices": len(bottom.data.vertices),
            "polygons": len(bottom.data.polygons),
            "vertexGroups": len(bottom.vertex_groups),
            "materials": [slot.material.name if slot.material else None for slot in bottom.material_slots],
        },
        "rig": {
            "name": rig.name,
            "bones": len(rig.data.bones),
            "deformBones": sum(bone.use_deform for bone in rig.data.bones),
        },
    },
    "outputs": {
        "blend": str(args.output_blend.resolve()),
        "blendSha256": sha256(args.output_blend),
        "fbx": str(args.output_fbx.resolve()),
        "fbxSha256": sha256(args.output_fbx),
    },
    "decision": "Use for extraction and weight-transfer POC only; replace with a higher-resolution outfit for final hero quality.",
}
args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
