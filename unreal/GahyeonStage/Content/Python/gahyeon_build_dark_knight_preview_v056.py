"""Import the modular Dark Knight fit proof and build a v056 desktop preview."""

from pathlib import Path

import unreal


SOURCE = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/donor-assets/dark-knight/"
    "v056/dark-knight-gahyeon-v056.fbx"
)
DESTINATION = "/Game/Gahyeon/CharacterPipeline/v056/DarkKnight"
ASSET = f"{DESTINATION}/SM_Gahyeon_DarkKnight_Modular_v056"
SOURCE_MAP = "/Game/Gahyeon/CharacterPipeline/v043/Preview/L_Skotukeda_SharpPOC_v043"
TARGET_MAP = "/Game/Gahyeon/CharacterPipeline/v056/Preview/L_Skotukeda_DarkKnight_v056"

if not SOURCE.is_file():
    raise RuntimeError(f"missing conformed Dark Knight FBX: {SOURCE}")
if unreal.EditorAssetLibrary.does_asset_exist(TARGET_MAP):
    raise RuntimeError(f"refusing to overwrite v056 map: {TARGET_MAP}")
if unreal.EditorAssetLibrary.does_asset_exist(ASSET):
    raise RuntimeError(f"refusing to overwrite v056 mesh: {ASSET}")

task = unreal.AssetImportTask()
task.set_editor_property("filename", str(SOURCE))
task.set_editor_property("destination_path", DESTINATION)
task.set_editor_property("destination_name", ASSET.rsplit("/", 1)[1])
task.set_editor_property("automated", True)
task.set_editor_property("replace_existing", False)
task.set_editor_property("save", True)
options = unreal.FbxImportUI()
options.set_editor_property("import_mesh", True)
options.set_editor_property("import_as_skeletal", False)
options.set_editor_property("import_materials", True)
options.set_editor_property("import_textures", True)
options.static_mesh_import_data.set_editor_property("combine_meshes", True)
options.static_mesh_import_data.set_editor_property("convert_scene", False)
options.static_mesh_import_data.set_editor_property("convert_scene_unit", False)
task.set_editor_property("options", options)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
mesh = unreal.EditorAssetLibrary.load_asset(ASSET)
if mesh is None or not isinstance(mesh, unreal.StaticMesh):
    raise RuntimeError(f"failed to import v056 armor: {ASSET}")

world = unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
if world is None:
    raise RuntimeError(f"failed to load stable source: {SOURCE_MAP}")
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
level_actors = actors.get_all_level_actors()
character = next(
    (actor for actor in level_actors if actor.get_actor_label() == "Skotukeda_Medium_v027"),
    None,
)
camera = next(
    (actor for actor in level_actors if actor.get_actor_label() == "CAM_Gahyeon_Desktop_v025b"),
    None,
)
if character is None or camera is None:
    raise RuntimeError("stable v043 character or camera is unavailable")

armor = actors.spawn_actor_from_class(
    unreal.StaticMeshActor, character.get_actor_location(), character.get_actor_rotation()
)
if armor is None:
    raise RuntimeError("failed to spawn v056 armor")
armor.set_actor_label("DarkKnight_Modular_StaticFit_v056")
armor.static_mesh_component.set_static_mesh(mesh)
camera.set_editor_property("auto_activate_for_player", unreal.AutoReceiveInput.PLAYER0)
if not unreal.EditorLoadingAndSavingUtils.save_map(world, TARGET_MAP):
    raise RuntimeError("failed to save populated Dark Knight v056")
unreal.log(f"Gahyeon Dark Knight v056 saved: {TARGET_MAP}")
