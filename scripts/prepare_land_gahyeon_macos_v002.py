"""Preserve the imported GLB's rig/animation and export an Unreal FBX interchange."""
import bpy
import hashlib
import json
from pathlib import Path
from mathutils import Vector

ROOT = Path('/Users/ze/work/gahyeonbot')
SOURCE = ROOT / 'artifacts/land-characters/land-tripo-20261015/gahyeon/tripo-v1/desktop/gahyeon-tripo-idle-v3.glb'
OUT = ROOT / 'artifacts/land-characters/macos-gahyeon-v001/interchange-v002'
OUT.mkdir(parents=True, exist_ok=False)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH' and any(m.type == 'ARMATURE' for m in o.modifiers)]
rigs = [o for o in bpy.context.scene.objects if o.type == 'ARMATURE']
assert len(rigs) == 1 and len(meshes) == 6
bpy.ops.object.select_all(action='DESELECT')
for obj in [*rigs, *meshes]: obj.select_set(True)
bpy.context.view_layer.objects.active = rigs[0]
bpy.context.scene.frame_end = int(max(a.frame_range[1] for a in bpy.data.actions))
points = [o.matrix_world @ Vector(p) for o in meshes for p in o.bound_box]
materials = []
for m in bpy.data.materials:
    textures = []
    if m.use_nodes:
        for node in m.node_tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                im = node.image
                path = OUT / (bpy.path.clean_name(im.name) + '.png')
                im.filepath_raw = str(path)
                im.file_format = 'PNG'
                im.save()
                textures.append({'node': node.name, 'path': str(path), 'colorspace': im.colorspace_settings.name})
    materials.append({'name': m.name, 'textures': textures})
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'Gahyeon_Land_Idle_v001.blend'))
bpy.ops.export_scene.fbx(filepath=str(OUT / 'Gahyeon_Land_Idle_v001.fbx'),
    use_selection=True, object_types={'ARMATURE', 'MESH'}, add_leaf_bones=False,
    bake_anim=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
    bake_anim_force_startend_keying=True, bake_anim_simplify_factor=0.0,
    path_mode='COPY', embed_textures=True, axis_forward='-Z', axis_up='Y')
report = {'source': str(SOURCE), 'sourceSha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    'meshes': [o.name for o in meshes], 'bones': len(rigs[0].data.bones),
    'boundsMin': [min(p[i] for p in points) for i in range(3)],
    'boundsMax': [max(p[i] for p in points) for i in range(3)],
    'actions': [a.name for a in bpy.data.actions], 'materials': materials,
    'fps': bpy.context.scene.render.fps, 'frameStart': bpy.context.scene.frame_start,
    'frameEnd': bpy.context.scene.frame_end, 'status': 'interchange-exported-not-visually-approved'}
(OUT / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
print('LAND_GAHYEON_EXPORT=' + json.dumps(report))
