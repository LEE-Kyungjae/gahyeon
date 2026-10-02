"""Import the transferred donor separates and build a static v055 preview."""

from pathlib import Path

import unreal


ROOT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/donor-assets/"
    "free-rigged-female/transferred"
)
SOURCES = {
    "top": ROOT / "gahyeon-donor-top-v054.fbx",
    "bottom": ROOT / "gahyeon-donor-bottom-v054.fbx",
}
DESTINATION = "/Game/Gahyeon/CharacterPipeline/v055/DonorOutfit"
ASSETS = {
    "top": f"{DESTINATION}/SM_Gahyeon_DonorTop_v055",
    "bottom": f"{DESTINATION}/SM_Gahyeon_DonorBottom_v055",
}
SOURCE_MAP = "/Game/Gahyeon/CharacterPipeline/v043/Preview/L_Skotukeda_SharpPOC_v043"
TARGET_MAP = "/Game/Gahyeon/CharacterPipeline/v055/Preview/L_Skotukeda_DonorOutfit_v055"
OFFICIAL_GARMENT = (
    "/MetaHumanCharacter/Optional/Clothing/DefaultGarment/ClothAssets/"
    "bodyShapeC/Meshes/DG_bodyShapeCcombined"
)

if unreal.EditorAssetLibrary.does_asset_exist(TARGET_MAP):
    raise RuntimeError(f"refusing to overwrite v055 map: {TARGET_MAP}")
official = unreal.EditorAssetLibrary.load_asset(OFFICIAL_GARMENT)
if official is None:
    raise RuntimeError("official garment materials are unavailable")

loaded = {}
for index, role in enumerate(("top", "bottom")):
    source = SOURCES[role]
    asset_path = ASSETS[role]
    if not source.is_file():
        raise RuntimeError(f"missing donor {role}: {source}")
    if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        raise RuntimeError(f"refusing to overwrite donor asset: {asset_path}")
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(source))
    task.set_editor_property("destination_path", DESTINATION)
    task.set_editor_property("destination_name", asset_path.rsplit("/", 1)[1])
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
    mesh = unreal.EditorAssetLibrary.load_asset(asset_path)
    if mesh is None or not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError(f"failed to import donor {role}: {asset_path}")
    mesh.set_material(0, official.get_material(index))
    unreal.EditorAssetLibrary.save_loaded_asset(mesh, only_if_is_dirty=False)
    loaded[role] = mesh

world = unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
if world is None:
    raise RuntimeError("failed to load stable v043 preview")
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
for role in ("top", "bottom"):
    actor = actors.spawn_actor_from_class(
        unreal.StaticMeshActor, character.get_actor_location(), character.get_actor_rotation()
    )
    if actor is None:
        raise RuntimeError(f"failed to spawn donor {role}")
    actor.set_actor_label(f"DonorOutfit_{role}_v055")
    actor.static_mesh_component.set_static_mesh(loaded[role])
camera.set_editor_property("auto_activate_for_player", unreal.AutoReceiveInput.PLAYER0)
if not unreal.EditorLoadingAndSavingUtils.save_map(world, TARGET_MAP):
    raise RuntimeError("failed to save populated donor-outfit v055")
unreal.log(f"Gahyeon donor outfit v055 saved: {TARGET_MAP}")
