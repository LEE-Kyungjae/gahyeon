import json
from pathlib import Path
import unreal

root = Path(__file__).resolve().parents[4]
config = json.loads((root / 'config/looking-glass-room-v011.json').read_text())
assert unreal.EditorLoadingAndSavingUtils.load_map(config['map'])
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
character = next(a for a in actors if isinstance(a, unreal.SkeletalMeshActor))
mesh = character.get_component_by_class(unreal.SkeletalMeshComponent)
assert mesh.get_skeletal_mesh_asset().get_path_name() == config['character']
assert mesh.get_editor_property('pause_anims')
camera = next(a for a in actors if isinstance(a, unreal.CineCameraActor))
assert abs(camera.get_actor_rotation().pitch + 1.5) < .01
assert abs(camera.get_actor_rotation().yaw + 90) < .01
room = [a for a in actors if a.get_actor_label().startswith('Room_')]
assert len(room) >= 74
assert all('/Land/Gahyeon/v004/' in m.get_path_name() for m in mesh.get_materials())
(root/'artifacts/looking-glass-room-v006/scene-validation.json').write_text(json.dumps({
    'passed':True,'map':config['map'],'roomActors':len(room),'characterIdentityPreserved':True,
    'originalMaterialsPreserved':True,'cameraRotation':str(camera.get_actor_rotation()),
    'execution':'PythonScriptCommandlet','humanApproved':False},indent=2)+'\n')

assert camera.camera_component.get_editor_property('focus_settings').get_editor_property('focus_method') == unreal.CameraFocusMethod.DISABLE
