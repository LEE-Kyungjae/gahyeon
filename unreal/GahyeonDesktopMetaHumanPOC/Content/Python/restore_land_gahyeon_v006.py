"""Restore the retained Gahyeon map without modifying the source world."""
import unreal,json
from pathlib import Path
SOURCE='/Game/Gahyeon/Land/Gahyeon/v004/Runtime/L_GahyeonLandMac_v004'
DEST='/Game/Gahyeon/Land/Gahyeon/v006/Runtime/L_GahyeonLandMac_v006'
assert not unreal.EditorAssetLibrary.does_asset_exist(DEST)
assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).new_level_from_template(DEST,SOURCE)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
character=next(a for a in actors if isinstance(a,unreal.SkeletalMeshActor))
component=character.get_component_by_class(unreal.SkeletalMeshComponent)
assert 'Gahyeon_Land_Idle_v001' in component.get_skeletal_mesh_asset().get_path_name(), 'Retained map identity changed'
assert all('/Land/Gahyeon/v004/' in m.get_path_name() for m in component.get_materials())
camera=next(a for a in actors if isinstance(a,unreal.CineCameraActor))
focus=camera.camera_component.get_editor_property('focus_settings')
focus.set_editor_property('focus_method',unreal.CameraFocusMethod.DISABLE)
camera.camera_component.set_editor_property('focus_settings',focus)
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert unreal.EditorLoadingAndSavingUtils.save_map(world,DEST)
Path('C:/GahyeonRuntime/roster-20261016/gahyeon-restoration.json').write_text(json.dumps({'map':DEST,'source':SOURCE,'mesh':component.get_skeletal_mesh_asset().get_path_name(),'materials':[m.get_path_name() for m in component.get_materials()]},indent=2))
unreal.SystemLibrary.quit_editor()
