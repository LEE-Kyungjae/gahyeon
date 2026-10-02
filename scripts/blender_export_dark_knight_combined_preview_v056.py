"""Export one combined static FBX while preserving the modular v056 Blender file."""

import sys
from pathlib import Path

import bpy


argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
if len(argv) != 1:
    raise SystemExit("usage: blender source.blend --python script.py -- output.fbx")
output = Path(argv[0])
if output.exists():
    raise RuntimeError(f"refusing to overwrite combined preview FBX: {output}")
output.parent.mkdir(parents=True, exist_ok=True)

sources = [obj for obj in bpy.data.objects if obj.type == "MESH" and obj.name.startswith("DK56_")]
if len(sources) < 4:
    raise RuntimeError(f"expected modular DK56 meshes, found {len(sources)}")
for obj in bpy.data.objects:
    obj.select_set(False)
duplicates = []
for source in sources:
    duplicate = source.copy()
    duplicate.data = source.data.copy()
    bpy.context.scene.collection.objects.link(duplicate)
    duplicate.select_set(True)
    duplicates.append(duplicate)
bpy.context.view_layer.objects.active = duplicates[0]
bpy.ops.object.join()
combined = bpy.context.view_layer.objects.active
combined.name = "SM_Gahyeon_DarkKnight_Combined_v056"
combined.data.name = f"{combined.name}_Mesh"
combined["source_modules"] = len(sources)
combined["preview_only"] = True
bpy.ops.export_scene.fbx(
    filepath=str(output.resolve()),
    use_selection=True,
    object_types={"MESH"},
    use_mesh_modifiers=True,
    add_leaf_bones=False,
    bake_anim=False,
    path_mode="COPY",
    embed_textures=True,
)
print(f"exported combined preview FBX with {len(sources)} source modules: {output}")
