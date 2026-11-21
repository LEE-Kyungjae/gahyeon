import json
from pathlib import Path
import unreal

assert '-run=pythonscript' in unreal.SystemLibrary.get_command_line().lower()
ROOT = Path(__file__).resolve().parents[4]
SOURCE = '/Game/Gahyeon/Land/Gahyeon/v009/Runtime/L_GahyeonRoom_v009'
DEST = '/Game/Gahyeon/Land/Gahyeon/v011/Runtime/L_GahyeonRoom_v011'
assert not unreal.EditorAssetLibrary.does_asset_exist(DEST), 'Preserve existing iterations'
if not unreal.EditorAssetLibrary.does_asset_exist(SOURCE):
    import runpy
    runpy.run_path(str(Path(__file__).with_name('build_gahyeon_room_v009.py')))
assert unreal.EditorLoadingAndSavingUtils.load_map(SOURCE)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
character = next(a for a in actors if isinstance(a, unreal.SkeletalMeshActor))
mesh = character.get_component_by_class(unreal.SkeletalMeshComponent)
assert 'Gahyeon_Land_Idle_v001' in mesh.get_skeletal_mesh_asset().get_path_name()
camera = next(a for a in actors if isinstance(a, unreal.CineCameraActor))
origin = camera.get_actor_location()
anchor = mesh.get_socket_location('head').y
depth_scale = 0.35
records = []
for actor in actors:
    if not isinstance(actor, unreal.StaticMeshActor) or not actor.get_actor_label().startswith('Room_'):
        continue
    if actor.get_actor_label().startswith(('Room_Floor', 'Room_Rug')):
        continue
    old = actor.get_actor_location()
    scale = actor.get_actor_scale3d()
    new_y = anchor + (old.y - anchor) * depth_scale
    ratio = (origin.y - new_y) / (origin.y - old.y)
    new = unreal.Vector(origin.x + (old.x-origin.x)*ratio, new_y, origin.z + (old.z-origin.z)*ratio)
    actor.set_actor_location(new, False, False)
    actor.set_actor_scale3d(unreal.Vector(scale.x*ratio, scale.y*depth_scale, scale.z*ratio))
    records.append(dict(name=actor.get_actor_label(), oldY=old.y, newY=new_y, projectedScale=ratio))
assert len(records) == 55
focus = camera.camera_component.get_editor_property('focus_settings')
focus.set_editor_property('focus_method', unreal.CameraFocusMethod.DISABLE)
camera.camera_component.set_editor_property('focus_settings', focus)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert unreal.EditorLoadingAndSavingUtils.save_map(world, DEST)
out = ROOT / 'artifacts/looking-glass-room-v006'
out.mkdir(parents=True, exist_ok=True)
(out/'scene.json').write_text(json.dumps(dict(status='candidate', humanApproved=False,
    source=SOURCE, map=DEST, depthScale=depth_scale, zeroParallaxY=anchor,
    character=mesh.get_skeletal_mesh_asset().get_path_name(),
    characterMaterials=[m.get_path_name() for m in mesh.get_materials()],
    roomActors=len(records), actors=records), indent=2))
