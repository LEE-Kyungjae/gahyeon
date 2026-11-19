"""Reconnect original GLB PBR channels lost by FBX and frame the actual character."""
import unreal,json,struct
from pathlib import Path
ROOT=Path('/Users/ze/work/gahyeonbot')
OUT=ROOT/'artifacts/land-characters/macos-gahyeon-v001'
DEST='/Game/Gahyeon/Land/Gahyeon/v004'
MAP=DEST+'/Runtime/L_GahyeonLandMac_v004'
assert not unreal.EditorAssetLibrary.does_directory_exist(DEST)
b=(ROOT/'artifacts/land-characters/land-tripo-20261015/gahyeon/tripo-v1/desktop/gahyeon-tripo-idle-v3.glb').read_bytes()
gltf=json.loads(b[20:20+struct.unpack_from('<I',b,12)[0]])
tools=unreal.AssetToolsHelpers.get_asset_tools()
texture_files=['gahyeon-tripo-star-textured-4k-v1_basecolor.png','gahyeon-corrected-basecolor-4096.png']
textures=[]
for i,name in enumerate(texture_files):
    t=unreal.AssetImportTask()
    t.filename=str(OUT/'interchange-v003'/name)
    t.destination_path=DEST+'/Textures'
    t.destination_name='T_Gahyeon_'+str(i)
    t.automated=True
    t.save=True
    tools.import_asset_tasks([t])
    textures.append(unreal.load_asset(t.imported_object_paths[0]))
materials=[]
for i,spec in enumerate(gltf['materials']):
    m=tools.create_asset('M_Gahyeon_'+str(i),DEST+'/Materials',unreal.Material,unreal.MaterialFactoryNew())
    m.set_editor_property('two_sided',spec.get('doubleSided',False))
    m.set_editor_property('used_with_skeletal_mesh',True)
    m.set_editor_property('used_with_morph_targets',True)
    p=spec['pbrMetallicRoughness']
    if 'baseColorTexture' in p:
        n=unreal.MaterialEditingLibrary.create_material_expression(m,unreal.MaterialExpressionTextureSample,-400,0)
        n.texture=textures[p['baseColorTexture']['index']]
        rg=unreal.MaterialEditingLibrary.create_material_expression(m,unreal.MaterialExpressionAppendVector,-250,0)
        rgb=unreal.MaterialEditingLibrary.create_material_expression(m,unreal.MaterialExpressionAppendVector,-100,0)
        assert unreal.MaterialEditingLibrary.connect_material_expressions(n,'R',rg,'A')
        assert unreal.MaterialEditingLibrary.connect_material_expressions(n,'G',rg,'B')
        assert unreal.MaterialEditingLibrary.connect_material_expressions(rg,'',rgb,'A')
        assert unreal.MaterialEditingLibrary.connect_material_expressions(n,'B',rgb,'B')
        assert unreal.MaterialEditingLibrary.connect_material_property(rgb,'',unreal.MaterialProperty.MP_BASE_COLOR)
    else:
        n=unreal.MaterialEditingLibrary.create_material_expression(m,unreal.MaterialExpressionConstant3Vector,-400,0)
        n.constant=unreal.LinearColor(*p.get('baseColorFactor',[1,1,1,1]))
        unreal.MaterialEditingLibrary.connect_material_property(n,'',unreal.MaterialProperty.MP_BASE_COLOR)
    for field,prop in [('metallicFactor',unreal.MaterialProperty.MP_METALLIC),('roughnessFactor',unreal.MaterialProperty.MP_ROUGHNESS)]:
        n=unreal.MaterialEditingLibrary.create_material_expression(m,unreal.MaterialExpressionConstant,-400,160)
        n.r=p.get(field,1)
        unreal.MaterialEditingLibrary.connect_material_property(n,'',prop)
    if spec.get('emissiveFactor'):
        n=unreal.MaterialEditingLibrary.create_material_expression(m,unreal.MaterialExpressionConstant3Vector,-400,260)
        n.constant=unreal.LinearColor(*spec['emissiveFactor'],1)
        unreal.MaterialEditingLibrary.connect_material_property(n,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    unreal.MaterialEditingLibrary.recompile_material(m)
    unreal.EditorAssetLibrary.save_loaded_asset(m)
    materials.append(m)
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Gahyeon/Land/Gahyeon/v002/Runtime/L_GahyeonLandMac_v002')
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
character=next(a for a in actors if isinstance(a,unreal.SkeletalMeshActor))
camera=next(a for a in actors if isinstance(a,unreal.CineCameraActor))
c=character.get_component_by_class(unreal.SkeletalMeshComponent)
assert len(c.get_materials())==len(materials)
for i,m in enumerate(materials): c.set_material(i,m)
camera.camera_component.set_editor_property('current_focal_length',60.0)
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert unreal.EditorLoadingAndSavingUtils.save_map(world,MAP)
r={'map':MAP,'materialPaths':[m.get_path_name() for m in materials],'texturePaths':[t.get_path_name() for t in textures],'sourceMaterialSpecs':gltf['materials'],'cameraFocalLength':60,'status':'candidate-visual-check-required'}
(OUT/'materials-v004-report.json').write_text(json.dumps(r,indent=2)+'\n')
unreal.SystemLibrary.quit_editor()
