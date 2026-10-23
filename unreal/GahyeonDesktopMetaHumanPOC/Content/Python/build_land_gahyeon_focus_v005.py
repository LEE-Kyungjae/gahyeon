import unreal,json
from pathlib import Path
out=Path('/Users/ze/work/gahyeonbot/artifacts/land-characters/macos-gahyeon-v001')
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Gahyeon/Land/Gahyeon/v004/Runtime/L_GahyeonLandMac_v004')
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
camera=next(a for a in actors if isinstance(a,unreal.CineCameraActor))
c=camera.camera_component
focus=c.get_editor_property('focus_settings')
before=str(focus)
focus.set_editor_property('focus_method',unreal.CameraFocusMethod.DISABLE)
c.set_editor_property('focus_settings',focus)
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
path='/Game/Gahyeon/Land/Gahyeon/v005/Runtime/L_GahyeonLandMac_v005'
assert unreal.EditorLoadingAndSavingUtils.save_map(world,path)
(out/'focus-v005-report.json').write_text(json.dumps({'map':path,'before':before,'after':str(c.get_editor_property('focus_settings'))},indent=2))
unreal.SystemLibrary.quit_editor()
