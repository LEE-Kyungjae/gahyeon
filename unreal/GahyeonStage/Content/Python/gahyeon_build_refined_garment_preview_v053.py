"""Build v053 directly from stable pre-garment v043 and add the v051 garment."""

import unreal


SOURCE_MAP = "/Game/Gahyeon/CharacterPipeline/v043/Preview/L_Skotukeda_SharpPOC_v043"
TARGET_MAP = "/Game/Gahyeon/CharacterPipeline/v053/Preview/L_Skotukeda_RefinedGarment_v053"
GARMENT_PATH = (
    "/Game/Gahyeon/CharacterPipeline/v051/Garment/"
    "SM_Skotukeda_DefaultGarment_Conformed_v051"
)

if unreal.EditorAssetLibrary.does_asset_exist(TARGET_MAP):
    raise RuntimeError(f"refusing to overwrite v053 map: {TARGET_MAP}")
garment = unreal.EditorAssetLibrary.load_asset(GARMENT_PATH)
if garment is None or not isinstance(garment, unreal.StaticMesh):
    raise RuntimeError(f"v051 garment is unavailable: {GARMENT_PATH}")
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

# Add before Save-As so the populated world and its new actor are sealed together.
new = actors.spawn_actor_from_class(
    unreal.StaticMeshActor, character.get_actor_location(), character.get_actor_rotation()
)
if new is None:
    raise RuntimeError("failed to spawn refined v053 garment")
new.set_actor_label("RefinedDefaultGarment_v053")
new.static_mesh_component.set_static_mesh(garment)
camera.set_editor_property("auto_activate_for_player", unreal.AutoReceiveInput.PLAYER0)
if not unreal.EditorLoadingAndSavingUtils.save_map(world, TARGET_MAP):
    raise RuntimeError("failed to Save-As populated v053")
unreal.log(f"Gahyeon refined populated v053 saved: {TARGET_MAP}")
