"""Build v052 directly from populated v045 using the imported v051 garment."""

import unreal


SOURCE_MAP = "/Game/Gahyeon/CharacterPipeline/v045/Preview/L_Skotukeda_DefaultGarment_v045"
TARGET_MAP = "/Game/Gahyeon/CharacterPipeline/v052/Preview/L_Skotukeda_RefinedGarment_v052"
GARMENT_PATH = (
    "/Game/Gahyeon/CharacterPipeline/v051/Garment/"
    "SM_Skotukeda_DefaultGarment_Conformed_v051"
)

if unreal.EditorAssetLibrary.does_asset_exist(TARGET_MAP):
    raise RuntimeError(f"refusing to overwrite v052 map: {TARGET_MAP}")
garment = unreal.EditorAssetLibrary.load_asset(GARMENT_PATH)
if garment is None or not isinstance(garment, unreal.StaticMesh):
    raise RuntimeError(f"v051 garment asset is unavailable: {GARMENT_PATH}")
world = unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
if world is None or not unreal.EditorLoadingAndSavingUtils.save_map(world, TARGET_MAP):
    raise RuntimeError("failed to Save-As v045 into v052")

actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
level_actors = actors.get_all_level_actors()
old = next(
    (actor for actor in level_actors if actor.get_actor_label() == "DefaultGarment_BodyShapeC_v045"),
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
    raise RuntimeError("populated v045 source actors are unavailable")
actors.destroy_actor(old)
new = actors.spawn_actor_from_class(
    unreal.StaticMeshActor, character.get_actor_location(), character.get_actor_rotation()
)
if new is None:
    raise RuntimeError("failed to spawn refined garment in v052")
new.set_actor_label("RefinedDefaultGarment_v052")
new.static_mesh_component.set_static_mesh(garment)
camera.set_editor_property("auto_activate_for_player", unreal.AutoReceiveInput.PLAYER0)
if not unreal.EditorLevelLibrary.save_current_level():
    raise RuntimeError("failed to save populated v052")
unreal.log(f"Gahyeon refined populated v052 saved: {TARGET_MAP}")
