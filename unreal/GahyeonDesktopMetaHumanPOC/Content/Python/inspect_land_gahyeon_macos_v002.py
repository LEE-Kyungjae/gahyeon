import unreal,json
from pathlib import Path
MAP='/Game/Gahyeon/Land/Gahyeon/v002/Runtime/L_GahyeonLandMac_v002'
unreal.EditorLoadingAndSavingUtils.load_map(MAP)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
character=next(a for a in actors if isinstance(a,unreal.SkeletalMeshActor))
camera=next(a for a in actors if isinstance(a,unreal.CineCameraActor))
c=character.get_component_by_class(unreal.SkeletalMeshComponent)
mesh=c.get_skeletal_mesh_asset()
anim=c.get_editor_property('animation_data').anim_to_play
r={'status':'candidate','map':MAP,'mesh':mesh.get_path_name().split('.')[0],'animation':anim.get_path_name().split('.')[0],'animationSeconds':anim.get_play_length(),'materials':[m.get_path_name() if m else None for m in c.get_materials()],'location':str(character.get_actor_location()),'rotation':str(character.get_actor_rotation()),'scale':str(character.get_actor_scale3d()),'bounds':[str(v) for v in character.get_actor_bounds(False)],'cameraLocation':str(camera.get_actor_location()),'cameraRotation':str(camera.get_actor_rotation())}
Path('/Users/ze/work/gahyeonbot/artifacts/land-characters/macos-gahyeon-v001/unreal-import-report.json').write_text(json.dumps(r,indent=2)+'\n')
unreal.SystemLibrary.quit_editor()
