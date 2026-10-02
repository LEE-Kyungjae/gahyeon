"""Import the combined Dark Knight proof and build a v057 desktop preview."""

from pathlib import Path

import unreal


SOURCE = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/donor-assets/dark-knight/"
    "v056/dark-knight-gahyeon-combined-v056.fbx"
)
DESTINATION = "/Game/Gahyeon/CharacterPipeline/v057/DarkKnight"
ASSET = f"{DESTINATION}/SM_Gahyeon_DarkKnight_Combined_v057"
SOURCE_MAP = "/Game/Gahyeon/CharacterPipeline/v043/Preview/L_Skotukeda_SharpPOC_v043"
TARGET_MAP = "/Game/Gahyeon/CharacterPipeline/v057/Preview/L_Skotukeda_DarkKnight_v057"

if not SOURCE.is_file():
    raise RuntimeError(f"missing combined Dark Knight FBX: {SOURCE}")
for asset in (ASSET, TARGET_MAP):
    if unreal.EditorAssetLibrary.does_asset_exist(asset):
        raise RuntimeError(f"refusing to overwrite v057 asset: {asset}")

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
    raise RuntimeError(f"failed to import v057 armor: {ASSET}")

world = unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
if world is None:
    raise RuntimeError(f"failed to load stable source: {SOURCE_MAP}")
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
level_actors = actors.get_all_level_actors()
character = next((actor for actor in level_actors if actor.get_actor_label() == "Skotukeda_Medium_v027"), None)
camera = next((actor for actor in level_actors if actor.get_actor_label() == "CAM_Gahyeon_Desktop_v025b"), None)
if character is None or camera is None:
    raise RuntimeError("stable v043 character or camera is unavailable")
armor = actors.spawn_actor_from_class(unreal.StaticMeshActor, character.get_actor_location(), character.get_actor_rotation())
if armor is None:
    raise RuntimeError("failed to spawn v057 armor")
armor.set_actor_label("DarkKnight_Combined_StaticFit_v057")
armor.static_mesh_component.set_static_mesh(mesh)
camera.set_editor_property("auto_activate_for_player", unreal.AutoReceiveInput.PLAYER0)
if not unreal.EditorLoadingAndSavingUtils.save_map(world, TARGET_MAP):
    raise RuntimeError("failed to save populated Dark Knight v057")
unreal.log(f"Gahyeon Dark Knight v057 saved: {TARGET_MAP}")
