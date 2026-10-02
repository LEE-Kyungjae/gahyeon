"""Import the Blender-conformed garment and build a non-destructive v048 preview."""

from pathlib import Path

import unreal


FBX = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/garment-conform/v048/"
    "output/skotukeda-garment-conformed-v048.fbx"
)
DESTINATION = "/Game/Gahyeon/CharacterPipeline/v048/Garment"
ASSET_NAME = "SM_Skotukeda_DefaultGarment_Conformed_v048"
ASSET_PATH = f"{DESTINATION}/{ASSET_NAME}"
SOURCE_MAP = "/Game/Gahyeon/CharacterPipeline/v043/Preview/L_Skotukeda_SharpPOC_v043"
TARGET_MAP = "/Game/Gahyeon/CharacterPipeline/v048/Preview/L_Skotukeda_ConformedGarment_v048"
SOURCE_GARMENT = (
    "/MetaHumanCharacter/Optional/Clothing/DefaultGarment/ClothAssets/"
    "bodyShapeC/Meshes/DG_bodyShapeCcombined"
)
CHARACTER_LABEL = "Skotukeda_Medium_v027"

if not FBX.is_file():
    raise RuntimeError(f"v048 conformed garment FBX is unavailable: {FBX}")
if unreal.EditorAssetLibrary.does_asset_exist(ASSET_PATH):
    raise RuntimeError(f"refusing to overwrite imported v048 garment: {ASSET_PATH}")
if unreal.EditorAssetLibrary.does_asset_exist(TARGET_MAP):
    raise RuntimeError(f"refusing to overwrite v048 preview: {TARGET_MAP}")

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
if garment is None or not isinstance(garment, unreal.StaticMesh):
    raise RuntimeError(f"v048 import did not produce the expected StaticMesh: {ASSET_PATH}")
source_garment = unreal.EditorAssetLibrary.load_asset(SOURCE_GARMENT)
if source_garment is None:
    raise RuntimeError(f"official source garment is unavailable: {SOURCE_GARMENT}")
for index in range(2):
    material = source_garment.get_material(index)
    if material is None:
        raise RuntimeError(f"official garment material slot {index} is empty")
    garment.set_material(index, material)
if not unreal.EditorAssetLibrary.save_loaded_asset(garment, only_if_is_dirty=False):
    raise RuntimeError("failed to save v048 conformed garment")

preview = unreal.EditorAssetLibrary.duplicate_asset(SOURCE_MAP, TARGET_MAP)
if preview is None:
    raise RuntimeError(f"failed to duplicate v048 preview source: {SOURCE_MAP}")
if not unreal.EditorLoadingAndSavingUtils.load_map(TARGET_MAP):
    raise RuntimeError(f"failed to load v048 preview: {TARGET_MAP}")

actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
character = next(
    (actor for actor in actors.get_all_level_actors() if actor.get_actor_label() == CHARACTER_LABEL),
    None,
)
if character is None:
    raise RuntimeError(f"character is unavailable: {CHARACTER_LABEL}")
garment_actor = actors.spawn_actor_from_class(
    unreal.StaticMeshActor,
    character.get_actor_location(),
    character.get_actor_rotation(),
)
if garment_actor is None:
    raise RuntimeError("failed to spawn v048 conformed garment")
garment_actor.set_actor_label("ConformedDefaultGarment_v048")
garment_actor.static_mesh_component.set_static_mesh(garment)

if not unreal.EditorLevelLibrary.save_current_level():
    raise RuntimeError("failed to save v048 conformed garment preview")
unreal.log(f"Gahyeon v048 conformed garment preview saved: {TARGET_MAP}")
