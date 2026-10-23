"""Import land's preserved Gahyeon and bind it to a copy of the canonical map."""
import json
from pathlib import Path
import unreal

ROOT = Path('/Users/ze/work/gahyeonbot')
OUT = ROOT / 'artifacts/land-characters/macos-gahyeon-v001'
SOURCE = OUT / 'interchange-v002/Gahyeon_Land_Idle_v001.fbx'
DEST = '/Game/Gahyeon/Land/Gahyeon/v001'
SOURCE_MAP = '/Game/Gahyeon/Character2/Diana/v398/Runtime/L_DianaMacRuntimeOriginalMaterialSafeFrame_v398'
MAP = DEST + '/Runtime/L_GahyeonLandMac_v001'
assert not unreal.EditorAssetLibrary.does_directory_exist(DEST), 'immutable destination exists'
task = unreal.AssetImportTask()
task.filename = str(SOURCE)
task.destination_path = DEST + '/Source'
task.automated = True
task.save = True
options = unreal.FbxImportUI()
options.set_editor_property('automated_import_should_detect_type', False)
options.import_mesh = True
options.import_as_skeletal = True
options.import_materials = True
options.import_textures = True
options.import_animations = True
options.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
options.skeletal_mesh_import_data.set_editor_property('convert_scene', True)
options.skeletal_mesh_import_data.set_editor_property('convert_scene_unit', True)
options.skeletal_mesh_import_data.set_editor_property('import_morph_targets', True)
task.options = options
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
paths = unreal.EditorAssetLibrary.list_assets(DEST, recursive=True, include_folder=False)
assets = [unreal.load_asset(p) for p in paths]
meshes = [a for a in assets if isinstance(a, unreal.SkeletalMesh)]
animations = [a for a in assets if isinstance(a, unreal.AnimSequence)]
assert len(meshes) == 1 and animations, [(str(a), a.get_class().get_name()) for a in assets]
mesh = meshes[0]
idle = max(animations, key=lambda a: a.get_play_length())
assert idle.get_play_length() > 10.0, 'idle animation was truncated'
unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actors = sub.get_all_level_actors()
character = next(a for a in actors if isinstance(a, unreal.SkeletalMeshActor))
camera = next(a for a in actors if isinstance(a, unreal.CineCameraActor))
component = character.get_component_by_class(unreal.SkeletalMeshComponent)
old_origin, old_extent = character.get_actor_bounds(False)
old_location = character.get_actor_location()
old_rotation = character.get_actor_rotation()
component.set_editor_property('override_materials', [])
component.set_skeletal_mesh_asset(mesh)
component.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
component.set_editor_property('animation_data', unreal.SingleAnimationPlayData(
    anim_to_play=idle, saved_looping=True, saved_playing=True, saved_position=0.0, saved_play_rate=1.0))
component.set_editor_property('forced_lod_model', 1)
character.set_actor_scale3d(unreal.Vector(1, 1, 1))
origin, extent = character.get_actor_bounds(False)
assert extent.z > 0
scale = old_extent.z / extent.z
character.set_actor_scale3d(unreal.Vector(scale, scale, scale))
origin, extent = character.get_actor_bounds(False)
character.set_actor_location(old_location + (old_origin - origin), False, False)
character.set_actor_label('Gahyeon_Land_Runtime_v001')
camera.set_actor_label('CAM_Gahyeon_Land_Runtime_v001')
assert unreal.EditorLoadingAndSavingUtils.save_map(world, MAP)
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
report = {'status': 'candidate-awaiting-visible-runtime-review', 'source': str(SOURCE),
    'mesh': mesh.get_path_name().split('.')[0], 'animation': idle.get_path_name().split('.')[0],
    'animationSeconds': idle.get_play_length(), 'map': MAP, 'sourceMap': SOURCE_MAP,
    'materials': [m.material_interface.get_path_name() if m.material_interface else None for m in mesh.materials],
    'oldLocation': str(old_location), 'oldRotation': str(old_rotation),
    'oldBounds': [str(old_origin), str(old_extent)], 'newBounds': [str(origin), str(extent)],
    'scale': scale, 'cameraLocation': str(camera.get_actor_location()),
    'cameraRotation': str(camera.get_actor_rotation()), 'importedAssets': list(paths)}
(OUT / 'unreal-import-report.json').write_text(json.dumps(report, indent=2) + '\n')
unreal.log('LAND_GAHYEON_RUNTIME=' + json.dumps(report))

unreal.SystemLibrary.quit_editor()
