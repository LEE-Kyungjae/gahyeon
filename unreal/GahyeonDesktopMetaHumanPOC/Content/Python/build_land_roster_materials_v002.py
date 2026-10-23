"""Restore exact source GLB texture routing in new, immutable runtime maps."""
import json, os, re
from pathlib import Path
import unreal
ROOT=Path(os.environ.get('GAHYEON_IMPORT_ROOT','/Users/ze/work/gahyeonbot'))
BASE=ROOT/'artifacts/land-characters/roster-20261016'
TOOLS=unreal.AssetToolsHelpers.get_asset_tools()
REPORT=[]
for ident in ['zeze','rogue','pirate','fighter','fighter-unmasked','child','hacker']:
    asset_id=ident.replace('-','_')
    dest='/Game/Gahyeon/Land/Roster_v002/'+asset_id
    assert not unreal.EditorAssetLibrary.does_directory_exist(dest), dest
    source=BASE/ident/'pbr'; gltf=json.loads((source/'gltf.json').read_text())
    textures=[]
    for i,image in enumerate(gltf['images']):
        extension={'image/png':'png','image/jpeg':'jpg'}[image['mimeType']]
        task=unreal.AssetImportTask();task.filename=str(source/f'image-{i}.{extension}')
        task.destination_path=dest+'/Textures';task.destination_name=f'T_{i}'
        task.automated=True;task.save=True;TOOLS.import_asset_tasks([task])
        textures.append(unreal.load_asset(task.imported_object_paths[0]))
    materials={}
    for i,spec in enumerate(gltf['materials']):
        m=TOOLS.create_asset(f'M_{i}',dest+'/Materials',unreal.Material,unreal.MaterialFactoryNew())
        m.set_editor_property('two_sided',spec.get('doubleSided',False))
        pbr=spec.get('pbrMetallicRoughness',{})
        if 'baseColorTexture' in pbr:
            image_index=gltf['textures'][pbr['baseColorTexture']['index']]['source']
            n=unreal.MaterialEditingLibrary.create_material_expression(m,unreal.MaterialExpressionTextureSample,-400,0)
            n.texture=textures[image_index]
            unreal.MaterialEditingLibrary.connect_material_property(n,'RGB',unreal.MaterialProperty.MP_BASE_COLOR)
        else:
            n=unreal.MaterialEditingLibrary.create_material_expression(m,unreal.MaterialExpressionConstant3Vector,-400,0)
            n.constant=unreal.LinearColor(*pbr.get('baseColorFactor',[1,1,1,1]))
            unreal.MaterialEditingLibrary.connect_material_property(n,'',unreal.MaterialProperty.MP_BASE_COLOR)
        for field,prop in [('metallicFactor',unreal.MaterialProperty.MP_METALLIC),('roughnessFactor',unreal.MaterialProperty.MP_ROUGHNESS)]:
            n=unreal.MaterialEditingLibrary.create_material_expression(m,unreal.MaterialExpressionConstant,-400,160)
            n.r=pbr.get(field,1)
            unreal.MaterialEditingLibrary.connect_material_property(n,'',prop)
        specular=spec.get('extensions',{}).get('KHR_materials_specular',{}).get('specularFactor',1)
        n=unreal.MaterialEditingLibrary.create_material_expression(m,unreal.MaterialExpressionConstant,-400,240)
        n.r=specular*0.5
        unreal.MaterialEditingLibrary.connect_material_property(n,'',unreal.MaterialProperty.MP_SPECULAR)
        unreal.MaterialEditingLibrary.recompile_material(m);unreal.EditorAssetLibrary.save_loaded_asset(m)
        materials[re.sub(r'[^a-z0-9]','',spec['name'].lower())]=m
    unreal.EditorLoadingAndSavingUtils.load_map('/Game/Gahyeon/Land/Roster_v001/'+asset_id+'/L_Character')
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    character=next(a for a in actors if isinstance(a,unreal.SkeletalMeshActor))
    component=character.get_component_by_class(unreal.SkeletalMeshComponent)
    bindings=[]
    for i,slot in enumerate(component.get_skeletal_mesh_asset().materials):
        key=re.sub(r'[^a-z0-9]','',slot.material_interface.get_name().lower())
        assert key in materials, (ident,key,list(materials))
        component.set_material(i,materials[key]);bindings.append(materials[key].get_path_name())
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    new_map=dest+'/L_Character'
    assert unreal.EditorLoadingAndSavingUtils.save_map(world,new_map)
    REPORT.append({'id':ident,'map':new_map,'materials':bindings,'textureCount':len(textures),'visualApproved':False})
    (BASE/'material-restoration-v002.json').write_text(json.dumps(REPORT,indent=2)+'\n')
unreal.SystemLibrary.quit_editor()
