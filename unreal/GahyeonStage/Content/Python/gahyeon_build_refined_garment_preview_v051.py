"""Import refined v051 garment and build a populated preview from v050."""

from pathlib import Path

import unreal


FBX = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/garment-conform/v051/"
    "output/skotukeda-garment-conformed-v051.fbx"
)
DESTINATION = "/Game/Gahyeon/CharacterPipeline/v051/Garment"
ASSET_NAME = "SM_Skotukeda_DefaultGarment_Conformed_v051"
ASSET_PATH = f"{DESTINATION}/{ASSET_NAME}"
SOURCE_MAP = "/Game/Gahyeon/CharacterPipeline/v050/Preview/L_Skotukeda_ConformedGarment_v050"
TARGET_MAP = "/Game/Gahyeon/CharacterPipeline/v051/Preview/L_Skotukeda_ConformedGarment_v051"
SOURCE_GARMENT = (
    "/MetaHumanCharacter/Optional/Clothing/DefaultGarment/ClothAssets/"
    "bodyShapeC/Meshes/DG_bodyShapeCcombined"
)

if not FBX.is_file():
    raise RuntimeError(f"v051 FBX is unavailable: {FBX}")
for target in (ASSET_PATH, TARGET_MAP):
    if unreal.EditorAssetLibrary.does_asset_exist(target):
        raise RuntimeError(f"refusing to overwrite v051 asset: {target}")

task = unreal.AssetImportTask()
task.set_editor_property("filename", str(FBX))
task.set_editor_property("destination_path", DESTINATION)
task.set_editor_property("destination_name", ASSET_NAME)
task.set_editor_property("automated", True)
task.set_editor_property("replace_existing", False)
task.set_editor_property("save", True)
options = unreal.FbxImportUI()
options.set_editor_property("import_mesh", True)
options.set_editor_property("import_as_skeletal", False)
options.set_editor_property("import_materials", False)
options.set_editor_property("import_textures", False)
options.static_mesh_import_data.set_editor_property("combine_meshes", True)
options.static_mesh_import_data.set_editor_property("convert_scene", False)
options.static_mesh_import_data.set_editor_property("convert_scene_unit", False)
task.set_editor_property("options", options)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

garment = unreal.EditorAssetLibrary.load_asset(ASSET_PATH)
official = unreal.EditorAssetLibrary.load_asset(SOURCE_GARMENT)
if garment is None or official is None:
    raise RuntimeError("v051 or official garment failed to load")
for index in range(2):
    material = official.get_material(index)
    if material is None:
        raise RuntimeError(f"official garment material slot {index} is empty")
    garment.set_material(index, material)
unreal.EditorAssetLibrary.save_loaded_asset(garment, only_if_is_dirty=False)

world = unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
if world is None or not unreal.EditorLoadingAndSavingUtils.save_map(world, TARGET_MAP):
    raise RuntimeError("failed to Save-As populated v051 preview")
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
level_actors = actors.get_all_level_actors()
old = next(
    (actor for actor in level_actors if actor.get_actor_label() == "ConformedDefaultGarment_v050"),
    None,
)
character = next(
    (actor for actor in level_actors if actor.get_actor_label() == "Skotukeda_Medium_v027"),
    None,
)
camera = next(
    (actor for actor in level_actors if actor.get_actor_label() == "CAM_Gahyeon_Desktop_v025b"),
    None,
)
if old is None or character is None or camera is None:
    raise RuntimeError("v051 source map did not retain garment, character, and camera")
actors.destroy_actor(old)
new = actors.spawn_actor_from_class(
    unreal.StaticMeshActor, character.get_actor_location(), character.get_actor_rotation()
)
if new is None:
    raise RuntimeError("failed to spawn v051 garment")
new.set_actor_label("ConformedDefaultGarment_v051")
new.static_mesh_component.set_static_mesh(garment)
camera.set_editor_property("auto_activate_for_player", unreal.AutoReceiveInput.PLAYER0)
if not unreal.EditorLevelLibrary.save_current_level():
    raise RuntimeError("failed to save v051 preview")
unreal.log(f"Gahyeon refined v051 preview saved: {TARGET_MAP}")
