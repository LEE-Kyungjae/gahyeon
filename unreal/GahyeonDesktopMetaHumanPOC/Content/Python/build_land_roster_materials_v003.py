"""Shared skeletal PBR master plus source-texture instances for the land roster."""
import json,os,re
from pathlib import Path
import unreal
ROOT=Path(os.environ.get('GAHYEON_IMPORT_ROOT','/Users/ze/work/gahyeonbot'))
BASE=ROOT/'artifacts/land-characters/roster-20261016'
DEST='/Game/Gahyeon/Land/Roster_v003'
TOOLS=unreal.AssetToolsHelpers.get_asset_tools()
master=unreal.load_asset(DEST+'/M_Roster')
if master is None:
    master=TOOLS.create_asset('M_Roster',DEST,unreal.Material,unreal.MaterialFactoryNew())
    master.set_editor_property('two_sided',True)
    master.set_editor_property('used_with_skeletal_mesh',True)
    master.set_editor_property('used_with_morph_targets',True)
    texture=unreal.MaterialEditingLibrary.create_material_expression(master,unreal.MaterialExpressionTextureSampleParameter2D,-500,0)
    texture.set_editor_property('parameter_name','BaseColor')
    texture.texture=unreal.load_asset('/Engine/EngineResources/WhiteSquareTexture')
    rg=unreal.MaterialEditingLibrary.create_material_expression(master,unreal.MaterialExpressionAppendVector,-250,0)
    rgb=unreal.MaterialEditingLibrary.create_material_expression(master,unreal.MaterialExpressionAppendVector,-100,0)
    assert unreal.MaterialEditingLibrary.connect_material_expressions(texture,'R',rg,'A')
    assert unreal.MaterialEditingLibrary.connect_material_expressions(texture,'G',rg,'B')
    assert unreal.MaterialEditingLibrary.connect_material_expressions(rg,'',rgb,'A')
    assert unreal.MaterialEditingLibrary.connect_material_expressions(texture,'B',rgb,'B')
    assert unreal.MaterialEditingLibrary.connect_material_property(rgb,'',unreal.MaterialProperty.MP_BASE_COLOR)
    for name,default,prop in [('Metallic',0,unreal.MaterialProperty.MP_METALLIC),('Roughness',0.6,unreal.MaterialProperty.MP_ROUGHNESS),('Specular',0.2,unreal.MaterialProperty.MP_SPECULAR)]:
        node=unreal.MaterialEditingLibrary.create_material_expression(master,unreal.MaterialExpressionScalarParameter,-400,200)
        node.set_editor_property('parameter_name',name);node.set_editor_property('default_value',default)
        assert unreal.MaterialEditingLibrary.connect_material_property(node,'',prop)
    unreal.MaterialEditingLibrary.recompile_material(master)
    unreal.EditorAssetLibrary.save_loaded_asset(master)
report=[]
for ident in ['zeze','rogue','pirate','fighter','fighter-unmasked','child','hacker']:
    asset_id=ident.replace('-','_');dest=DEST+'/'+asset_id
    assert not unreal.EditorAssetLibrary.does_asset_exist(dest+'/L_Character'), 'completed map is immutable'
    source=BASE/ident/'pbr';gltf=json.loads((source/'gltf.json').read_text());textures=[]
    for i,image in enumerate(gltf['images']):
        extension={'image/png':'png','image/jpeg':'jpg'}[image['mimeType']]
        task=unreal.AssetImportTask();task.filename=str(source/f'image-{i}.{extension}')
        task.destination_path=dest+'/Textures';task.destination_name=f'T_{i}';task.automated=True;task.save=True
        existing=unreal.load_asset(dest+f'/Textures/T_{i}')
        if existing is None:
            TOOLS.import_asset_tasks([task]);existing=unreal.load_asset(task.imported_object_paths[0])
        textures.append(existing)
    materials={}
    for i,spec in enumerate(gltf['materials']):
        assert spec.get('doubleSided') and spec.get('alphaMode','OPAQUE')=='OPAQUE'
        pbr=spec['pbrMetallicRoughness'];assert not spec.get('normalTexture') and not spec.get('emissiveFactor')
        assert not pbr.get('baseColorFactor')
        material=TOOLS.create_asset(f'MI_{i}_source',dest+'/Materials',unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
        unreal.MaterialEditingLibrary.set_material_instance_parent(material,master)
        image_index=gltf['textures'][pbr['baseColorTexture']['index']]['source']
        unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(material,'BaseColor',textures[image_index])
        assert unreal.MaterialEditingLibrary.get_material_instance_texture_parameter_value(material,'BaseColor') == textures[image_index]
        specular=spec.get('extensions',{}).get('KHR_materials_specular',{}).get('specularFactor',1)
        for name,value in [('Metallic',pbr.get('metallicFactor',1)),('Roughness',pbr.get('roughnessFactor',1)),('Specular',specular*0.5)]:
            unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(material,name,value)
            assert abs(unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(material,name)-value) < 0.00001
        unreal.MaterialEditingLibrary.update_material_instance(material);unreal.EditorAssetLibrary.save_loaded_asset(material)
        materials[re.sub(r'[^a-z0-9]','',spec['name'].lower())]=material
    new_map=dest+'/L_Character'
    assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).new_level_from_template(new_map,'/Game/Gahyeon/Land/Roster_v001/'+asset_id+'/L_Character')
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    character=next(a for a in actors if isinstance(a,unreal.SkeletalMeshActor))
    component=character.get_component_by_class(unreal.SkeletalMeshComponent);bindings=[]
    for i,slot in enumerate(component.get_skeletal_mesh_asset().materials):
        key=re.sub(r'[^a-z0-9]','',slot.material_interface.get_name().lower());assert key in materials
        component.set_material(i,materials[key]);bindings.append(materials[key].get_path_name())
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world();new_map=dest+'/L_Character'
    assert unreal.EditorLoadingAndSavingUtils.save_map(world,new_map)
    report.append({'id':ident,'map':new_map,'materials':bindings,'textureCount':len(textures),'visualApproved':False})
    (BASE/'material-restoration-v003.json').write_text(json.dumps(report,indent=2)+'\n')
unreal.SystemLibrary.quit_editor()
