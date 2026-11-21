import json
import os
from pathlib import Path
import unreal

root = Path(__file__).resolve().parents[4]
iteration = os.environ.get('GAHYEON_ROOM_DETAIL_ITERATION', 'v013')
assert iteration in ('v012', 'v013')
config = json.loads((root/('config/looking-glass-room-' + iteration + '.json')).read_text())
subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assert unreal.EditorLoadingAndSavingUtils.load_map(config['fallbackMap'])
old = subsystem.get_all_level_actors()
old_mesh = next(a for a in old if isinstance(a, unreal.SkeletalMeshActor)).skeletal_mesh_component
baseline_materials = [m.get_path_name() for m in old_mesh.get_materials()]
old_camera = next(a for a in old if isinstance(a, unreal.CineCameraActor))
baseline_camera = str(old_camera.get_actor_transform())
assert unreal.EditorLoadingAndSavingUtils.load_map(config['map'])
actors = subsystem.get_all_level_actors()
mesh = next(a for a in actors if isinstance(a, unreal.SkeletalMeshActor)).skeletal_mesh_component
camera = next(a for a in actors if isinstance(a, unreal.CineCameraActor))
assert mesh.get_skeletal_mesh_asset().get_path_name() == config['character']
assert [m.get_path_name() for m in mesh.get_materials()] == baseline_materials
assert str(camera.get_actor_transform()) == baseline_camera
assert camera.camera_component.get_editor_property('focus_settings').get_editor_property('focus_method') == unreal.CameraFocusMethod.DISABLE
labels = [a.get_actor_label() for a in actors]
for prefix in ('Room_Detail_WindowCasing','Room_Detail_SkylineFar','Room_Detail_SkylineNear','Room_Detail_Curtain','Room_Detail_DrawerFace','Room_Detail_Wainscot'):
    assert any(label.startswith(prefix) for label in labels), prefix
details = [a for a in actors if a.get_actor_label().startswith('Room_Detail_')]
assert 70 <= len(details) <= 150
assert all(a.static_mesh_component.get_material(0) is not None for a in details)
assert all(min(a.get_actor_scale3d().x, a.get_actor_scale3d().y, a.get_actor_scale3d().z) > 0 for a in details)
(root/('artifacts/looking-glass-room-' + iteration)/'scene-validation.json').write_text(json.dumps(dict(
    passed=True,characterIdentityPreserved=True,originalMaterialsPreserved=True,cameraPreserved=True,
    detailActors=len(details),liveWeather=False,humanApproved=False),indent=2)+'\n')
